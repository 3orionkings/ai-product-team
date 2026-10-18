# Negative access test matrix

Longer material for `aipt-method-retrieval-and-context-contracts` (S15). The SKILL.md Method is authoritative; this file shows how to enumerate the tests so none of the stores is skipped.

## Enumerate the matrix

1. List the scope boundaries: every ordered pair of principals or principal classes that must not see each other's content. For two workspaces this is two pairs (`ws-alpha` requesting `ws-beta`, and the reverse); do not assume symmetry is tested by one direction.
2. List the stores from the transformation inventory: the primary store, each chunk store, each embedding index, each summary store, each cache, each search index.
3. The matrix is boundaries multiplied by stores. Every cell is one negative test. A cell left empty is a finding, not an omission to tidy later.

## Test record shape

```json
{
  "test_id": "NT-02",
  "boundary": "ws-alpha -> ws-beta",
  "store": "ticket-embeddings",
  "requesting_principal": "agent@ws-alpha",
  "target_scope": "ws-beta",
  "setup": "one ticket in ws-beta whose text matches the query exactly",
  "request": "nearest-neighbor query for that text as agent@ws-alpha",
  "expected": "denied",
  "expected_evidence": ["zero results", "denial event with requester, target scope and store"],
  "status": "planned",
  "receipt_ref": null,
  "verifies": "REQ-isolation-001@v1"
}
```

A test moves from `planned` to `receipted` only when a receipt exists: the recorded command, exit status and target versions, as `aipt-method-evaluation-execution-and-receipts` (S19) defines. A test that passed against an older version keeps its historical pass; its applicability to the current version is unestablished until it is run again.

## Setups that catch common gaps

- **Exact-match setup.** Place content in the forbidden scope that matches the query exactly, so a leak cannot hide behind low relevance.
- **Cache warm setup.** Run the authorized principal first so the cache is warm, then run the forbidden principal with the same content; the expected outcome is still `denied`.
- **Multi-source derived setup.** Create a summary derived from one record in each workspace; the expected outcome is that the summary does not exist or is visible to neither principal.
- **Instruction-in-content setup.** Place a document in the forbidden scope whose text asks the reader to include it anyway; the expected outcome is `denied`, and the assembled context contains no trace of it.

## Positive companion

For each boundary, one positive test shows the authorized principal receives its own content with `source_id`, scope and `retrieved_at` markers intact after assembly. A positive test never substitutes for a negative one.
