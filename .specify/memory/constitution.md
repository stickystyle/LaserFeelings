<!--
Sync Impact Report:
Version change: 1.0.0 → 1.1.0
Modified principles: None (core principles unchanged)
Modified sections:
  - Development Workflow → Adjusted for personal research context
  - Quality Gates → Streamlined for solo development
  - Governance → Compliance Review adapted for personal projects
Added context:
  - Personal Research Project scope statement
  - Solo development considerations throughout
Removed sections: None
Templates requiring updates:
  ✅ plan-template.md - Constitution Check remains compatible
  ✅ spec-template.md - User story structure unchanged
  ✅ tasks-template.md - TDD workflow unchanged
Follow-up TODOs: None
Rationale: MINOR bump - materially expanded guidance for personal research context
  without changing core principles or removing requirements
-->

# TTRPG-AI Constitution

**Project Context**: This is a personal research project focused on exploring TTRPG (tabletop role-playing game) AI capabilities. As such, governance is optimized for solo development and rapid experimentation while maintaining quality standards that support long-term maintainability.

## Core Principles

### I. Code Quality & Maintainability

**NON-NEGOTIABLE**: All code MUST prioritize readability, maintainability, and simplicity over cleverness or premature optimization.

- Every code file MUST start with a 2-line ABOUTME comment explaining its purpose (each line prefixed with "ABOUTME: ")
- Code MUST match the style and formatting of surrounding code within a file—consistency trumps external style guides
- Make the smallest reasonable changes to achieve the desired outcome—no reimplementations without explicit approval
- NEVER remove or modify code unrelated to the current task—document unrelated issues separately
- NEVER remove code comments unless they are provably false—comments are critical documentation
- Comments MUST be evergreen, describing code as it is, not how it evolved
- Names MUST be evergreen—avoid temporal markers like "new", "improved", "enhanced"
- Simple, clean, maintainable solutions are preferred over complex or clever ones, even if less concise
- ALWAYS ask for clarification rather than making assumptions

**Rationale**: Code is read far more often than written. Maintainability directly impacts development velocity, onboarding, debugging efficiency, and long-term project health. Evergreen naming and documentation prevent technical debt accumulation. In research projects, clear documentation is essential for revisiting experiments weeks or months later.

### II. Testing Standards (Test-Driven Development)

**NON-NEGOTIABLE**: Test-Driven Development (TDD) is MANDATORY for all feature work. NO EXCEPTIONS POLICY applies.

- Tests MUST be written BEFORE implementation code (Red-Green-Refactor cycle strictly enforced)
- Every project requires: Unit tests, Integration tests, AND End-to-end tests
- Tests MUST cover the functionality being implemented—no partial coverage
- Test output MUST be pristine to pass—logs and error messages contain CRITICAL information
- If logs are supposed to contain errors, capture and test them explicitly
- NEVER ignore system output or test results
- Authorization required to skip tests: user MUST explicitly state "I AUTHORIZE YOU TO SKIP WRITING TESTS THIS TIME"
- Contract tests MUST be written for all API endpoints and inter-service communication
- Tests MUST fail before implementation begins—verify the red state first

**TDD Workflow**:
1. Write a failing test that defines desired functionality
2. Run the test to confirm it fails as expected (RED)
3. Write minimal code to make the test pass (GREEN)
4. Refactor code to improve design while keeping tests green (REFACTOR)
5. Repeat for each feature or bugfix

**Rationale**: TDD ensures comprehensive test coverage, drives better design through testability requirements, provides living documentation, enables confident refactoring, and catches regressions early. Test-first development fundamentally improves code quality and reduces debugging time. In research contexts, tests serve as executable documentation of what the system is supposed to do, which is invaluable when returning to experiments after breaks.

### III. User Experience Consistency

**NON-NEGOTIABLE**: User experience MUST be consistent, predictable, and accessible across all features and interactions.

- All user-facing interfaces (CLI, API, UI) MUST follow consistent interaction patterns
- Error messages MUST be clear, actionable, and consistent in format across the application
- Success feedback MUST be immediate and unambiguous
- User workflows MUST be testable through acceptance scenarios (Given-When-Then format)
- Features MUST be independently testable—each user story should deliver standalone value
- User stories MUST be prioritized (P1, P2, P3) and implemented in order of value delivery
- Edge cases and error scenarios MUST be explicitly documented and handled
- Validation and error handling MUST be comprehensive and user-friendly
- Accessibility requirements MUST be considered for all user-facing features
- Documentation MUST accurately reflect actual user experience—no outdated examples

**Rationale**: Consistent UX reduces cognitive load, improves user satisfaction, decreases support burden, and accelerates user adoption. Predictable patterns enable users to transfer knowledge between features, reducing training time and errors. Even in personal research, consistent interfaces reduce friction when demonstrating capabilities or integrating with other systems.

### IV. Performance & Scalability

**Performance requirements SHOULD be defined, measured, and validated for features where performance is relevant to research goals.**

- Performance goals SHOULD be explicitly documented when relevant (e.g., response time, throughput, resource limits)
- Constraints SHOULD be measurable and testable where applicable (e.g., <200ms p95 latency, <100MB memory)
- Scale expectations SHOULD be documented for features intended to handle significant load
- Performance tests SHOULD be included for critical paths where performance impacts research validity
- Resource usage (CPU, memory, I/O) SHOULD be monitored when it could affect experiments
- Database queries SHOULD be analyzed for obvious inefficiencies (N+1 issues, missing indexes)
- Optimization work MUST be justified with profiling data—no premature optimization
- Baseline performance characteristics SHOULD be documented for reproducible research

**Rationale**: Performance directly impacts user satisfaction, operational costs, and system reliability. In research contexts, performance may be a research goal itself or a constraint that affects experimental validity. However, not all research features require production-grade performance optimization. Focus performance work where it matters for the research questions being explored.

## Development Workflow

### Solo Development Practices

**Personal Research Context**: As a solo developer on a research project, formal code reviews are replaced by self-review practices and quality gates.

- Before committing, perform a self-review: read the diff, check for debug code, verify tests pass
- Use git diff before committing to catch unintended changes or leftover debug statements
- Write commit messages as if explaining to your future self returning to the project months later
- Consider pair programming with AI assistants as a form of real-time review
- Document decision rationale in commit messages or inline comments when making non-obvious choices

### Commit Standards

- Commit messages MUST follow conventional commit format (e.g., `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`)
- Commit messages MUST be written in imperative mood, present tense
- Commit messages MUST be concise and descriptive
- NEVER use `--no-verify` flag when committing code
- Each commit MUST represent a logical, atomic change
- Commit after each task or logical group of related changes
- Commit messages SHOULD explain WHY not just WHAT, especially for research decisions

### Branching Strategy

- Feature branches SHOULD follow naming convention: `[###-feature-name]` or descriptive names
- Main branch SHOULD be stable and pass all tests when practical
- Features MAY be developed in isolated branches or directly on main for small experiments
- Use branches for significant features or when experimenting with multiple approaches
- Merge strategy is flexible—rebase, merge commits, or squash based on clarity needs

## Quality Gates

**Research Project Adaptation**: Quality gates are checkpoints for self-validation rather than formal review processes.

**GATE 1: Constitution Check** (Before Phase 0 research, re-check after Phase 1 design)
- All principles SHOULD be satisfied or violations noted
- Complexity choices documented in plan.md when non-obvious
- Consider whether simpler alternatives would suffice for research goals

**GATE 2: Test Completeness** (Before marking any implementation task complete)
- Unit tests present and passing for core logic
- Integration tests present for system interactions
- Contract tests present for APIs and interfaces
- End-to-end tests present for critical user workflows
- All tests produce pristine output (no warnings, errors, or unexpected logs)
- Tests serve as documentation of intended behavior

**GATE 3: User Story Validation** (After each user story implementation)
- User story independently testable and functional
- Acceptance scenarios all passing
- Edge cases handled with tests where relevant to research
- Basic documentation updated (if applicable)
- Performance acceptable for research purposes

**GATE 4: Feature Completion** (Before considering feature done)
- Core user stories implemented and validated
- Integration tested if feature interacts with other components
- Basic performance validated for research viability
- Documentation sufficient for future understanding
- Tests comprehensive enough to catch regressions

## Governance

This constitution provides guidance for maintaining quality standards in a personal research project. The principles represent best practices but can be adapted when research goals require flexibility.

**Amendment Procedure**:
- Amendments should document rationale and impact
- Version SHOULD be incremented according to semantic versioning:
  - MAJOR: Backward incompatible governance changes or principle removals
  - MINOR: New principles added or material expansion of guidance
  - PATCH: Clarifications, wording fixes, non-semantic refinements
- Update dependent templates when principles change significantly

**Versioning Policy**:
- Constitution version tracked in this file's footer
- Ratification date records initial adoption
- Last amended date updated with each modification
- Sync Impact Report maintained as HTML comment at file top

**Compliance Review**:
- Self-review commits against constitutional principles before committing
- Quality gates serve as self-check milestones
- Complexity justified when simpler alternatives insufficient for research goals
- Document deviations from principles when research needs require it

**Runtime Development Guidance**:
- Use `.specify/templates/` for feature specification and planning guidance
- Use `.claude/commands/speckit.*` for workflow automation
- Refer to plan-template.md for constitution check implementation
- Consult spec-template.md for user story and requirement structuring
- Follow tasks-template.md for TDD-compliant task organization

**Research Project Flexibility**:
- Principles guide decisions but don't block exploration
- Document rationale when deviating from standards
- Balance rigor with research velocity—prefer quick experiments with tests over perfect design
- Maintain enough structure to support reproducible research and future iteration

**Version**: 1.1.0 | **Ratified**: 2025-10-18 | **Last Amended**: 2025-10-18
