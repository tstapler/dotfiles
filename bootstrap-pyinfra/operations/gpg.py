"""
pyinfra's built-in gpg module (pyinfra.operations.gpg) only manages keys/
keyrings — there's no signature-verification operation (confirmed against
pyinfra 3.9.2). This fills that one gap.
"""

from collections.abc import Generator

from pyinfra.api import operation  # type: ignore[attr-defined]  # pyinfra/#439


@operation()
def verify(signature: str, target: str, keyring: str) -> Generator[str]:
    """
    Verify a detached GPG signature against a target file using an isolated
    keyring, so it doesn't touch the user's real GPG keyring. Fails the
    deploy (non-zero exit) if verification fails — this is a gate, not
    stateful config, so it always runs rather than checking for idempotency.

    + signature: path to the detached .sig file
    + target: path to the file being verified
    + keyring: path to a scratch keyring file containing only the trusted key
    """
    yield f'gpg --no-default-keyring --keyring "{keyring}" --verify "{signature}" "{target}"'
