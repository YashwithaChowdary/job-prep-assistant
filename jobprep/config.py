"""Feature switches. Every switch can be turned off independently, which is
what the ablation study (jobprep/ablation.py) does to measure what each
design decision is worth."""
from dataclasses import dataclass, replace


@dataclass(frozen=True)
class Config:
    use_aliases: bool = True        # match "k8s", "Postgres", "GH Actions" ... not just canonical names
    use_implied: bool = True        # pandas -> Python
    use_related: bool = True        # AWS <-> Azure earns partial credit
    use_jd_sections: bool = True    # read Requirements / Nice-to-have / About-us headings
    use_negation: bool = True       # "no experience with X", "currently learning X"

    def without(self, **flags) -> "Config":
        return replace(self, **{k: False for k in flags})


DEFAULT = Config()

# credit given to each gap status when scoring
CREDIT = {"matched": 1.0, "partial": 0.5, "missing": 0.0}
# weight of each requirement tier
WEIGHT = {"required": 1.0, "preferred": 0.5}
# fit bands on the 0-100 score
FIT_STRONG, FIT_MODERATE = 75, 50
