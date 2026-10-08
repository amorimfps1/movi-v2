import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import {
  ChevronLeft,
  RefreshCw,
  Pencil,
  ClipboardCheck,
  CalendarDays,
} from "lucide-react";
import type { RecordData } from "./types";
import { useAuth, isAdmin } from "./auth";
import { useApi } from "./query";
import { post } from "./api";
import { ResourceList } from "./resources";
import { lessonSpec, classSpec } from "./schema";
import { RecordForm } from "./forms";
import {
  PageTitle,
  Loading,
  ErrorNotice,
  Button,
  Notice,
  Badge,
  Empty,
  Confirm,
} from "./ui";
import { date, today, timestamp } from "./format";
import { RecordDetail } from "./RecordDetail";
type Roster = {
  lesson: number;
  version: string;
  participants: { enrollment: number; student_name: string }[];
  excluded: { enrollment: number; reason: string; decisions: string[] }[];
  decisions: string[];
};
type RecordedAttendance = {
  lesson: number;
  status: string;
  marks: {
    enrollment: number;
    student_name: string;
    present: boolean;
    created_at: string;
  }[];
  definition: string;
};
export function AcademicList({ classes = false }: { classes?: boolean }) {
  const { user } = useAuth();
  const admin = isAdmin(user);
  return (
    <ResourceList
      key={classes ? "classes" : "lessons"}
      eyebrow={admin ? "ROTINA DA SECRETARIA" : "SEU DIÁRIO"}
      spec={{
        ...(classes ? classSpec : lessonSpec),
        readOnly: !admin,
        ...(!admin
          ? {
              description: classes
                ? "Consulte as turmas e os encontros sob sua responsabilidade."
                : "Consulte as aulas e a chamada no seu diário autorizado.",
            }
          : {}),
      }}
      beforeList={
        !admin && (
          <Notice>
            Este diário contém somente turmas e aulas autorizadas para o seu
            vínculo profissional. Alterações de oferta e substituição cabem à
            equipe administrativa.
          </Notice>
        )
      }
    />
  );
}
export function ClassDetail() {
  const { user } = useAuth();
  return <RecordDetail spec={{ ...classSpec, readOnly: !isAdmin(user) }} />;
}
export function LessonDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const admin = isAdmin(user);
  const query = useApi<RecordData>(`lessons/${id}/`);
  const roster = useApi<Roster>(
    `lessons/${id}/roster/`,
    query.data?.status === "scheduled",
  );
  const attendance = useApi<RecordedAttendance>(
    `lessons/${id}/attendance/`,
    query.data?.status === "completed",
  );
  const [marks, setMarks] = useState<Record<number, boolean>>({});
  const [editing, setEditing] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [success, setSuccess] = useState("");
  const client = useQueryClient();
  if (query.isPending) return <Loading />;
  if (query.error) return <ErrorNotice error={query.error} />;
  if (!query.data) return null;
  const lesson = query.data;
  const blocked = !!roster.data?.decisions.length;
  const complete =
    !!roster.data?.participants.length &&
    roster.data.participants.every(
      (participant) => typeof marks[participant.enrollment] === "boolean",
    );
  const canSubmit =
    lesson.status === "scheduled" &&
    !blocked &&
    lesson.date === today() &&
    complete;
  async function refresh() {
    setMarks({});
    setSuccess("");
    if (lesson.status === "scheduled") await roster.refetch();
    if (lesson.status === "completed") await attendance.refetch();
    await query.refetch();
  }
  return (
    <>
      <Link className="back-link" to="/aulas">
        <ChevronLeft size={16} />
        Aulas e chamada
      </Link>
      <PageTitle
        eyebrow={`DIÁRIO · AULA #${id}`}
        title={String(lesson.class_name)}
        description={`${date(lesson.date)} · ${String(lesson.instructor_name)}`}
        actions={
          admin &&
          lesson.status !== "completed" && (
            <Button variant="secondary" onClick={() => setEditing(true)}>
              <Pencil size={17} />
              Editar aula / substituição
            </Button>
          )
        }
      />
      {success && <Notice tone="success">{success}</Notice>}
      <section className="lesson-heading">
        <div>
          <CalendarDays size={22} />
          <span>
            <small>Data do encontro</small>
            <strong>{date(lesson.date)}</strong>
          </span>
        </div>
        <div>
          <small>Responsável</small>
          <strong>{String(lesson.instructor_name)}</strong>
        </div>
        <Badge value={lesson.status} />
      </section>
      {lesson.status === "completed" && (
        <Notice tone="success">
          Aula realizada e chamada concluída. Correções e reabertura aguardam
          política própria, DN-014.
        </Notice>
      )}
      {lesson.status === "cancelled" && (
        <Notice tone="warning">
          Aula cancelada. A chamada está indisponível e a reabertura depende de
          DN-015.
        </Notice>
      )}
      <section className="sheet roster-sheet">
        <div className="section-heading">
          <div>
            <p className="eyebrow">CADERNO DE CHAMADA</p>
            <h2>
              {lesson.status === "completed"
                ? "Frequência registrada"
                : "Alunos elegíveis"}
            </h2>
          </div>
          <Button
            variant="secondary"
            onClick={() => void refresh()}
            disabled={roster.isFetching || attendance.isFetching}
          >
            <RefreshCw size={17} />
            Atualizar diário
          </Button>
        </div>
        {lesson.status === "completed" ? (
          attendance.isPending ? (
            <Loading />
          ) : attendance.error ? (
            <div className="section-pad">
              <ErrorNotice error={attendance.error} />
            </div>
          ) : (
            attendance.data && (
              <>
                <div className="section-pad">
                  <Notice>{attendance.data.definition}</Notice>
                </div>
                {attendance.data.marks.length ? (
                  <div className="table-scroll">
                    <table>
                      <thead>
                        <tr>
                          <th>Aluno</th>
                          <th>Frequência</th>
                          <th>Registrada em</th>
                        </tr>
                      </thead>
                      <tbody>
                        {attendance.data.marks.map((mark) => (
                          <tr key={mark.enrollment}>
                            <td>
                              <strong>{mark.student_name}</strong>
                              <small>Matrícula #{mark.enrollment}</small>
                            </td>
                            <td>
                              <Badge
                                value={mark.present ? "regular" : "neutral"}
                              >
                                {mark.present ? "Presente" : "Ausente"}
                              </Badge>
                            </td>
                            <td>{timestamp(mark.created_at)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <Empty
                    title="Sem marcações disponíveis"
                    description="Consulte a equipe responsável para conferir o histórico desta aula."
                  />
                )}
                <p className="report-definition">
                  Registros preservados da conclusão da aula. Indicadores
                  agregados de frequência e alertas aguardam DN-018. Correção e
                  reabertura aguardam DN-014.
                </p>
              </>
            )
          )
        ) : lesson.status !== "scheduled" ? (
          <Empty
            title={
              lesson.status === "completed"
                ? "Chamada concluída e preservada"
                : "Aula cancelada"
            }
            description={
              lesson.status === "completed"
                ? "A consulta individual das marcações registradas ainda não está disponível. Indicadores históricos de frequência aguardam DN-018; correção e reabertura aguardam DN-014."
                : "Não há chamada disponível para esta aula. Reabertura depende da política DN-015."
            }
          />
        ) : roster.isPending ? (
          <Loading />
        ) : roster.error ? (
          <div className="section-pad">
            <ErrorNotice error={roster.error} />
          </div>
        ) : (
          roster.data && (
            <>
              <div className="section-pad">
                {blocked && (
                  <Notice tone="warning">
                    <strong>
                      Chamada indisponível: decisões institucionais pendentes.
                    </strong>
                    <br />A lista e a elegibilidade dependem de definições
                    aprovadas. Decisões: {roster.data.decisions.join(", ")}. Não
                    há confirmação de participação enquanto essas condições não
                    forem resolvidas.
                  </Notice>
                )}
                {lesson.date !== today() && lesson.status === "scheduled" && (
                  <Notice tone="warning">
                    Chamada fora da data atual depende de política institucional
                    específica. DN-014.
                  </Notice>
                )}
                {!!lesson.notes && (
                  <p className="lesson-notes">{String(lesson.notes)}</p>
                )}
              </div>
              {!roster.data.participants.length ? (
                <Empty
                  title="Nenhum aluno elegível nesta lista"
                  description="A ausência de alunos não conclui a aula. Consulte as matrículas e as políticas de participação."
                />
              ) : (
                <form
                  onSubmit={(event) => {
                    event.preventDefault();
                    if (canSubmit) setConfirming(true);
                  }}
                >
                  <div className="table-scroll">
                    <table>
                      <thead>
                        <tr>
                          <th>Aluno</th>
                          <th>Marcação de frequência</th>
                        </tr>
                      </thead>
                      <tbody>
                        {roster.data.participants.map((participant) => (
                          <tr key={participant.enrollment}>
                            <td>
                              <strong>{participant.student_name}</strong>
                              <small>Matrícula #{participant.enrollment}</small>
                            </td>
                            <td>
                              <fieldset
                                className="attendance-options"
                                disabled={
                                  blocked || lesson.status !== "scheduled"
                                }
                              >
                                <legend className="sr-only">
                                  Frequência de {participant.student_name}
                                </legend>
                                <label>
                                  <input
                                    type="radio"
                                    name={`presence-${participant.enrollment}`}
                                    value="present"
                                    required
                                    checked={
                                      marks[participant.enrollment] === true
                                    }
                                    onChange={() =>
                                      setMarks({
                                        ...marks,
                                        [participant.enrollment]: true,
                                      })
                                    }
                                  />
                                  Presente
                                </label>
                                <label>
                                  <input
                                    type="radio"
                                    name={`presence-${participant.enrollment}`}
                                    value="absent"
                                    required
                                    checked={
                                      marks[participant.enrollment] === false
                                    }
                                    onChange={() =>
                                      setMarks({
                                        ...marks,
                                        [participant.enrollment]: false,
                                      })
                                    }
                                  />
                                  Ausente
                                </label>
                              </fieldset>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <div className="roster-submit">
                    <p>
                      Uma marcação por matrícula.
                      <br />
                      <small>
                        A autorização e a lista são verificadas novamente na
                        confirmação.
                      </small>
                    </p>
                    <Button type="submit" disabled={!canSubmit}>
                      <ClipboardCheck size={18} />
                      Concluir chamada e aula
                    </Button>
                  </div>
                </form>
              )}
              {roster.data.excluded.length > 0 && (
                <details className="excluded-list">
                  <summary>
                    {roster.data.excluded.length} vínculo
                    {roster.data.excluded.length === 1 ? "" : "s"} fora da
                    chamada
                  </summary>
                  <ul>
                    {roster.data.excluded.map((item, index) => (
                      <li key={item.enrollment}>
                        <strong>
                          {admin
                            ? `Matrícula #${item.enrollment}`
                            : `Vínculo indisponível ${index + 1}`}
                        </strong>
                        <p>{item.reason}</p>
                        {item.decisions.length > 0 && (
                          <small>{item.decisions.join(", ")}</small>
                        )}
                      </li>
                    ))}
                  </ul>
                </details>
              )}
            </>
          )
        )}
      </section>
      {editing && (
        <RecordForm
          title="Editar aula e atribuição"
          endpoint="lessons/"
          fields={lessonSpec.fields}
          record={lesson}
          onClose={() => setEditing(false)}
          onSaved={() => {
            setMarks({});
            setSuccess(
              "Aula atualizada. Confira a lista antes de registrar frequência.",
            );
          }}
        />
      )}
      {confirming && roster.data && (
        <Confirm
          title="Concluir chamada e aula?"
          description={`Serão registradas ${roster.data.participants.length} marcações. ${Object.values(marks).filter(Boolean).length} presenças e ${Object.values(marks).filter((value) => !value).length} ausências. A aula será concluída junto com a chamada.`}
          confirm="Confirmar chamada"
          onClose={() => setConfirming(false)}
          action={async () => {
            await post(`lessons/${id}/attendance/`, {
              version: roster.data!.version,
              marks: roster.data!.participants.map((participant) => ({
                enrollment: participant.enrollment,
                present: marks[participant.enrollment],
              })),
            });
            await client.invalidateQueries();
            setSuccess("Chamada e aula concluídas juntas com sucesso.");
          }}
        />
      )}
    </>
  );
}
