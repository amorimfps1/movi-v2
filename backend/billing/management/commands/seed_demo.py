"""Explicit, idempotent fixture for an isolated development database."""
from datetime import timedelta
from decimal import Decimal
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from core.models import User, Student, Modality, Instructor, ClassGroup, Lead, OperationLock
from core.audit import record
from billing.models import Enrollment, CommercialCondition, Charge, Payment
from academic.models import Lesson


class Command(BaseCommand):
    help = 'Cria dados sintéticos identificados em banco exclusivo de desenvolvimento.'

    def add_arguments(self, parser):
        parser.add_argument('--password', required=True, help='Senha local para as três contas demo, mínimo 12 caracteres.')

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG or not settings.DEMO_MODE:
            raise CommandError('Exige DEBUG=true e DEMO_MODE=true. Nunca execute no banco de operação.')
        password = options['password']
        if len(password) < 12:
            raise CommandError('Use senha local de pelo menos 12 caracteres.')
        marker = OperationLock.objects.filter(key='demo-seeded').exists()
        if not marker and (Student.objects.exists() or User.objects.exists()):
            raise CommandError('O banco já contém cadastros. Use um banco vazio exclusivo para demonstração.')
        today = timezone.localdate()
        accounts = {}
        for email, first, role in [
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
            student,_ = Student.objects.get_or_create(name=f'Participante {index+1:02} • demonstração',
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
        User.objects.get_or_create(email='solicitante@example.test',defaults={
            'username':'solicitante-demo','first_name':'Solicitante • demonstração','access_status':'pending'})
        OperationLock.objects.get_or_create(key='demo-seeded')
        self.stdout.write(self.style.SUCCESS('Demonstração pronta. Contas secretaria@example.test, instrutor@example.test, comunicacao@example.test. Use a senha fornecida no comando. Propostas e políticas continuam pendentes.'))
