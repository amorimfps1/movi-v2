"""Explicit, idempotent fixture for an isolated development database."""
from datetime import date, timedelta
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from core.models import User, Person, Modality, Instructor, ClassGroup, Lead, OperationLock
from core.audit import record
from billing.models import Enrollment, CommercialCondition, Charge, Payment
from billing.contracts import terms, generate
from academic.models import Lesson


class Command(BaseCommand):
    help = 'Cria dados sintéticos identificados em banco exclusivo de desenvolvimento.'

    def add_arguments(self, parser):
        parser.add_argument('--password', required=True, help='Senha local para as quatro contas demo, mínimo 12 caracteres. Contas existentes mantêm a senha.')
        parser.add_argument('--date', type=date.fromisoformat, help='Data de referência AAAA-MM-DD (padrão: hoje). Contratos exigem 2026.')

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG or not settings.DEMO_MODE:
            raise CommandError('Exige DEBUG=true e DEMO_MODE=true. Nunca execute no banco de operação.')
        password = options['password']
        if len(password) < 12:
            raise CommandError('Use senha local de pelo menos 12 caracteres.')
        # Serialize seed invocations; the transaction rolls this lock back on failure.
        lock, _ = OperationLock.objects.get_or_create(key='demo-seed-lock')
        OperationLock.objects.select_for_update().get(pk=lock.pk)
        marker = OperationLock.objects.filter(key='demo-seeded').exists()
        if not marker and any(model.objects.exists() for model in (
            Person, User, Modality, Instructor, ClassGroup, Lead, Enrollment, Lesson,
        )):
            raise CommandError('O banco já contém cadastros. Use um banco vazio exclusivo para demonstração.')
        reference = OperationLock.objects.filter(key__startswith='demo-reference-date:').first()
        today = date.fromisoformat(reference.key.split(':', 1)[1]) if reference else options['date'] or timezone.localdate()
        if reference and options['date'] and options['date'] != today:
            raise CommandError('O seed já tem outra data de referência. Use um banco demo separado para outro cenário.')
        if OperationLock.objects.filter(key='demo-contracts-v1').exists():
            self.stdout.write(self.style.SUCCESS(f'Seed já aplicado (referência {today}). Dados e senhas preservados.'))
            return
        if today.year != 2026:
            raise CommandError('A tabela contratual disponível é de 2026. Informe --date 2026-11-04 para uma demonstração histórica.')
        if today > timezone.localdate():
            raise CommandError('A data de referência não pode estar no futuro.')
        accounts = {}
        for email, first, role in [
            ('coordenacao@example.test','Coordenação • demonstração','coordinator'),
            ('secretaria@example.test','Secretaria • demonstração','secretary'),
            ('instrutor@example.test','Instrutor • demonstração','instructor'),
            ('comunicacao@example.test','Comunicação • demonstração','communication'),
        ]:
            user, created = User.objects.get_or_create(email=email,defaults={'username':email,'first_name':first,
                'roles':[role],'access_status':'approved'})
            if created:
                user.set_password(password)
                user.save()
            accounts[role] = user
        admin = accounts['secretary']
        if not marker:
            self.seed_legacy(today, accounts, admin)
        self.seed_contracts(today, accounts)
        pending, created = User.objects.get_or_create(email='solicitante@example.test',defaults={
            'username':'solicitante-demo','first_name':'Solicitante • demonstração','access_status':'pending'})
        if created or not pending.password:
            pending.set_unusable_password()
            pending.save(update_fields=['password'])
        OperationLock.objects.get_or_create(key='demo-seeded')
        OperationLock.objects.get_or_create(key=f'demo-reference-date:{today.isoformat()}')
        OperationLock.objects.create(key='demo-contracts-v1')
        self.stdout.write(self.style.SUCCESS(
            f'Demonstração pronta (referência {today}). Contas: coordenacao@example.test, '
            'secretaria@example.test, instrutor@example.test, comunicacao@example.test. '
            'Novas contas usam a senha fornecida; contas existentes mantêm a senha. '
            'Dados sintéticos; políticas e configurações não foram alteradas.'
        ))

    def seed_legacy(self, today, accounts, admin):
        modality_names = [('Música','Cultura','120.00'),('Dança','Movimento','90.00'),
                          ('Teatro','Cultura','100.00'),('Artes visuais','Criação','80.00')]
        groups = []
        for index,(name,area,price) in enumerate(modality_names):
            modality,_ = Modality.objects.get_or_create(name=name,defaults={'area':area,'default_price':price})
            instructor,_ = Instructor.objects.get_or_create(name=f'Equipe {index+1} • demonstração',
                defaults={'email':f'equipe{index+1}@example.test','user':accounts['instructor'] if index == 0 else None})
            instructor.specialties.add(modality)
            hour = 8+index*2
            group,_ = ClassGroup.objects.get_or_create(name=f'{name} • turma de demonstração',defaults={
                'modality':modality,'instructor':instructor,'weekdays':[today.weekday()],
                'start_time':f'{hour:02}:00','end_time':f'{hour+1:02}:00','room':f'Sala {index+1}',
                'age_range':'A definir pela oferta','capacity':20,'allows_trial':False})
            groups.append(group)
            Lesson.objects.get_or_create(class_group=group,date=today)
        for index in range(8):
            student,_ = Person.objects.get_or_create(name=f'Participante {index+1:02} • demonstração',
                defaults={'email':f'participante{index+1}@example.test','notes':'Registro sintético para desenvolvimento; sem dados pessoais reais.'})
            group = groups[index%len(groups)]
            enrollment,created = Enrollment.objects.get_or_create(student=student,class_group=group,
                defaults={'start_date':today-timedelta(days=20),'plan':'monthly','amount':group.modality.default_price})
            if created:
                CommercialCondition.objects.create(enrollment=enrollment,amount=enrollment.amount,
                    plan=enrollment.plan,effective_on=enrollment.start_date,actor=admin,reason='Condição sintética de demonstração.')
            charge,_ = Charge.objects.get_or_create(enrollment=enrollment,category='tuition',competence=today.replace(day=1),
                defaults={'due_date':today-timedelta(days=3) if index%3 == 0 else today+timedelta(days=5),
                          'amount':enrollment.amount,'description':'Cobrança avulsa sintética; não representa política de recorrência.'})
            if index%3 == 1:
                payment,payment_created = Payment.objects.get_or_create(charge=charge,defaults={
                    'amount':charge.amount,'paid_on':today,'method':'pix','actor':admin,'reference':'DEMONSTRAÇÃO'})
                if payment_created:
                    record(admin,'payment.received',payment,metadata={'demo':True,'amount':str(payment.amount)})
        for index,source in enumerate(['Indicação','Visita ao espaço','Redes sociais']):
            lead,_ = Lead.objects.get_or_create(name=f'Interessado {index+1:02} • demonstração',
                defaults={'email':f'interessado{index+1}@example.test','source':source,'status':['new','contacting','waiting'][index]})
            lead.interests.add(groups[index].modality)

    def seed_contracts(self, today, accounts):
        actor = accounts['coordinator']
        instructor = Instructor.objects.get(user=accounts['instructor'])
        groups = []
        for category, fee_kind in [(1, 'standard'), (2, 'rhythmic')]:
            # Dedicated synthetic offers do not assign real activities to price categories.
            modality = Modality.objects.create(
                name=f'Atividade contratual {category} • demonstração', area='Teste de contratos',
                default_price='0.00', price_category=category, enrollment_fee_kind=fee_kind,
            )
            instructor.specialties.add(modality)
            group = ClassGroup.objects.create(
                name=f'Contratos {category} • turma de demonstração', modality=modality,
                instructor=instructor, weekdays=[today.weekday()], start_time=f'{16+category}:00',
                end_time=f'{17+category}:00', room=f'Sala contratos {category}', capacity=20,
            )
            groups.append(group)
            for offset in [0, 7]:
                Lesson.objects.create(class_group=group, date=today + timedelta(days=offset),
                                      notes='Aula sintética para teste de chamada.')

        scenarios = [
            ('Regular trimestral', 'quarterly', 3, False, 'current', today),
            ('Aguardando ativação', 'quarterly', 2, True, 'unpaid', today),
            ('Parcela em atraso' if today > date(2026, 1, 15) else 'Aguardando vencimento',
             'quarterly', 3, False, 'unpaid', max(date(2026, 1, 1), today - timedelta(days=35))),
            ('Cancelado', 'yearly', 12, True, 'cancelled', today),
            ('Regular anual associado', 'yearly', 6, True, 'current', today),
            ('Somente taxa paga', 'quarterly', 1, False, 'fee_only', today),
        ]
        students = []
        for index, (label, plan, installments, associated, state, start) in enumerate(scenarios):
            student = Person.objects.create(
                name=f'{label} • demonstração', email=f'contrato{index+1}@example.test',
                notes='Registro sintético para testes; sem dados pessoais reais.',
            )
            students.append(student)
            group = groups[index % len(groups)]
            enrollment = Enrollment.objects.create(
                student=student, class_group=group, start_date=start, plan=plan,
                associated=associated, payment_method='card', installments=installments,
                **terms(group, start, plan, associated, 'card', installments),
            )
            CommercialCondition.objects.create(
                enrollment=enrollment, amount=enrollment.amount, plan=plan, effective_on=start,
                actor=actor, reason='Condição sintética de demonstração.',
            )
            record(actor, 'enrollment.created', enrollment, metadata={'demo': True})
            generate(enrollment, actor)
            for charge in enrollment.charges.all():
                activation = charge.category == 'enrollment_fee' or charge.idempotency_key.endswith(':installment:1')
                should_pay = (state in ('current', 'cancelled') and (activation or charge.due_date <= today)
                              or state == 'fee_only' and charge.category == 'enrollment_fee')
                if should_pay:
                    payment = Payment.objects.create(
                        charge=charge, amount=charge.amount, paid_on=today, method='card',
                        actor=actor, reference='DEMONSTRAÇÃO',
                    )
                    record(actor, 'payment.received', payment, metadata={'demo': True, 'amount': str(payment.amount)})
            if state == 'cancelled':
                enrollment.administrative_status = 'cancelled'
                enrollment.save(update_fields=['administrative_status'])
                record(actor, 'enrollment.cancelled', enrollment, reason='Cancelamento sintético de demonstração.', metadata={'demo': True})

        for status, student in [('converted', students[0]), ('not_converted', None)]:
            lead = Lead.objects.create(
                name=f'Interessado {status} • demonstração', email=f'{status}@example.test',
                source='Demonstração', status=status, student=student,
                notes='Registro sintético para teste do funil comercial.',
            )
            lead.interests.add(groups[0].modality)
