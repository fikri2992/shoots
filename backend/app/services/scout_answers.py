"""Resolve one stored Scout Question with Photographer-owned authority."""

from app.domain import taxonomy
from app.domain.entities import (
    PhotographerSignal,
    PhotographerSignalKind,
    ScoutAnswer,
    ScoutAnswerState,
    ScoutRoute,
    SignalScope,
    SignalSource,
)
from app.infra import repository as repo
from app.services import photographer_memory
from app.services import scout as experiment_scout
from app.services.context import Context


class AnswerConflict(ValueError):
    pass


async def answer(
    ctx: Context,
    user_id: str,
    shoot_id: str,
    revision: int,
    option_id: str,
) -> ScoutAnswer:
    record = await repo.find_shoot_record(ctx.store, shoot_id, revision)
    if record is None or record.user_id != user_id:
        raise repo.UnknownEntity(f"Shoot Record {shoot_id} revision {revision}")
    decision = record.scout
    if decision.route is not ScoutRoute.ASK or not decision.question.id:
        raise AnswerConflict("This Shoot Record has no open Scout Question")
    option = next((item for item in decision.question.options if item.id == option_id), None)
    if option is None:
        raise AnswerConflict("The selected answer is not one of this Question's options")

    pending = ScoutAnswer(
        id=decision.question.id,
        user_id=user_id,
        question_id=decision.question.id,
        shoot_id=shoot_id,
        shoot_revision=revision,
        option_id=option.id,
        technique_id=option.technique_id,
    )
    claimed, created = await repo.claim_scout_answer(ctx.store, pending)
    if not created and claimed.option_id != option.id:
        raise AnswerConflict(
            "This Question already has a different answer; intervention history was not rewritten"
        )
    if claimed.state is ScoutAnswerState.COMPLETED:
        return claimed

    value = (
        f"I was exploring {taxonomy.BY_ID[option.technique_id].name}."
        if option.technique_id
        else "I was just shooting freely."
    )
    signal_id = photographer_memory.stable_signal_id(
        user_id,
        SignalScope.SHOOT,
        shoot_id,
        PhotographerSignalKind.INTENT,
        value,
        f"scout_answer:{decision.question.id}",
    )
    signal = PhotographerSignal(
        id=signal_id,
        user_id=user_id,
        scope=SignalScope.SHOOT,
        scope_id=shoot_id,
        kind=PhotographerSignalKind.INTENT,
        value=value,
        source=SignalSource.PHOTOGRAPHER_ACTION,
        source_event_id=f"evt_{decision.question.id}_answered",
    )
    await photographer_memory.apply_photographer_signal(ctx, signal)

    experiment_id = ""
    detail = "Intent recorded; no Experiment was requested."
    if option.technique_id:
        experiment = await experiment_scout.issue_explore(
            ctx,
            user_id,
            technique_id=option.technique_id,
            requested_reason=(
                f"You said {taxonomy.BY_ID[option.technique_id].name} was the decision "
                "you were exploring in this Shoot."
            ),
            experiment_id=f"experiment_{shoot_id}_r{revision}",
            warrant_shot_ids=list(
                dict.fromkeys(
                    shot_id
                    for warrant in decision.warrant
                    if warrant.technique_id == option.technique_id
                    for shot_id in warrant.shot_ids
                )
            ),
            selection_basis="shoot_intent_answer",
        )
        if experiment is not None:
            experiment_id = experiment.id
            detail = "Intent recorded and corrected Explore offered."
        else:
            detail = "Intent recorded; another Experiment currently owns the open slot."

    claimed.intent_signal_id = signal.id
    claimed.experiment_id = experiment_id
    claimed.state = ScoutAnswerState.COMPLETED
    claimed.detail = detail
    await repo.put_scout_answer(ctx.store, claimed)
    await repo.record(
        ctx.store,
        user_id,
        "scout",
        "question_answered",
        {
            "question_id": claimed.question_id,
            "shoot_id": shoot_id,
            "revision": revision,
            "option_id": option.id,
            "technique_id": option.technique_id,
            "intent_signal_id": signal.id,
            "experiment_id": experiment_id,
        },
        experiment_id=experiment_id,
    )
    return claimed
