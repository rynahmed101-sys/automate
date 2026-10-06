# Research and Evidence Boundary

The Worker may search external material, but retrieved material is evidence, not authority.

Every accepted research source carries:
- source type;
- stable locator;
- title;
- retrieval timestamp;
- SHA-256 content digest;
- optional query and claim;
- optional notes.

The digest binds the evidence record to the retrieved material without pretending that the source itself is correct.

Automate may later connect this contract to web search, papers, GitHub, databases, and datasets. Each adapter must preserve provenance and return UNKNOWN rather than inventing missing evidence.

Research retrieval must remain bounded. A Worker gets a task-specific query budget and source limit, not unrestricted access to the internet.

The intended flow is:

research request -> bounded retrieval -> provenance packet -> worker reasoning -> independent verification -> Automate decision

A source may support a claim, contradict it, or merely provide context. The Worker must preserve that distinction.
