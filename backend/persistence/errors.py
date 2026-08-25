class PersistenceError(Exception):
    """
    Raised when the data handed to persistence cannot be stored without
    silently corrupting the audit trail -- a missing candidate-row linkage, a
    malformed shape, an unknown audit stage.

    Never raised because persistence disagrees with a decision. Persistence
    has no opinion on outcomes, scores, or authorization; this exception is
    about integrity of the write, not correctness of the pipeline's decision.
    """
