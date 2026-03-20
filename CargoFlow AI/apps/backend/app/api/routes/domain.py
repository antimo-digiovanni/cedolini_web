from fastapi import APIRouter

from app.schemas.domain import DomainSummaryResponse, EntitySummary

router = APIRouter(prefix="/domain", tags=["domain"])


@router.get("/summary", response_model=DomainSummaryResponse)
def domain_summary() -> DomainSummaryResponse:
    return DomainSummaryResponse(
        bounded_contexts=[
            "identity-and-access",
            "fleet-and-compliance",
            "load-marketplace",
            "trip-execution",
            "trust-and-billing",
        ],
        entities=[
            EntitySummary(name="Company", description="Azienda trasportatrice verificata e proprietaria della flotta."),
            EntitySummary(name="User", description="Utente autenticato con ruolo operativo o amministrativo."),
            EntitySummary(name="Vehicle", description="Mezzo configurato con allestimenti e certificazioni."),
            EntitySummary(name="Load", description="Carico pubblicato con vincoli logistici e finestra temporale."),
            EntitySummary(name="Auction", description="Asta associata a un carico con timer e regole di assegnazione."),
            EntitySummary(name="Trip", description="Missione assegnata a un autista con tracking e stati operativi."),
        ],
    )
