# DIE-H01 Evidence Prioritization v1

H01-133 is a deterministic, non-mutating projection over the H01-101 queue. It may reorder only remaining work. Already-produced semantic masters are emitted as `PRESERVED_PRODUCED`, receive no new rank, and retain `produced_master_validity_effect=NONE`.

Remaining items use normalized evidence from accepted H01 contracts. The v1 score weights H01-130 demand at 60%, H01-131 competition opportunity at 25%, and H01-130 confidence at 15%. Missing components are omitted and the available weights are renormalized. Confidence alone cannot create a ranked item. Items with no usable market evidence remain `UNRANKED`, remain production-valid, and keep H01-101 source order after ranked items.

H01-130 family discoveries remain `HYPOTHESIS`. Family priority is the mean priority of ranked remaining members. H01-133 never promotes a hypothesis into canonical H01-120 Family state.

The projection never mutates queue identity, Object Atlas validity, rights, feasibility, or produced-master validity. It grants no production, submission, publication, or spend authority. H01-132 Human Atlas context remains bounded hypothesis context with no independent rank authority.
