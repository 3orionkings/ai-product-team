"""AI Product Team: experimental record-keeping library behind the agents, skills and workflows.

STATUS: experimental. The shipped product is the agent, skill and workflow files under agents/, skills/,
workflows/ and dist/. This library is not connected to either host and has no command-line interface.
Implemented and unit-tested: validation, storage, registry, policies, lineage, decisions, routing,
receipts. Incomplete and untested: controller. Not built: reporting, cli, fixture runner.

The controller validates records, transitions, authority and independence. It does not judge evidence,
run inference or perform external actions. See docs/architecture/controller-contracts.md.
"""

__version__ = "0.1.0"
PACKAGE_NAME = "ai-product-team"
