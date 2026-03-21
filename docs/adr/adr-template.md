> [!check]
> **General Instructions**
> - **Tone**: Maintain a professional and precise style, using accurate technical terminology
>   from the programming and software architecture domain.
> - **Content**: Prioritize clarity and conciseness. Present information in a structured and
>   direct manner. Avoid redundancy, repetitions and unnecessary reformulations.
> - **Placeholders**: Replace all uppercase square-bracketed placeholders (e.g., `[PLACEHOLDER]`)
>   with the appropriate content.
> - **Adherence to Structure**: Strictly follow the provided format and content guidelines to
>   maintain consistency across ADRs.
> - **Final Cleanup**: Remove all instruction blocks marked with the `" > "` sign, including this
>   section and the glossary. Keep the delimiter lines (e.g., `---`) to separate sections clearly.

# ADR [00XX]: [TITLE]

**Status**: [Proposed | Accepted | Rejected | Deprecated | Superseded by ADR-00YY]

---

## Problem Statement

> [!check]
> - Describe the problem, requirement, context or motivation in a few sentences.
> - Formulate clear and specific question(s) that the decision should answer (preferably a single
>   one, or a restricted set of _related_ questions if relevant).
> - Formulate one precise and well-scoped question that the decision should answer. If multiple
>   questions are necessary, ensure they are closely related. Focus on specific questions that
>   directly drive architectural choices.

[...DESCRIPTION...]

**Questions to be addressed**:
1. [QUESTION1] ?
2. [QUESTION2] ?

---

## Decision Drivers

> [!check]
> - Select *a few* decision drivers from the glossary at the end of the document (e.g., modularity,
>   flexibility...). Choose only the most relevant drivers for the current context (maximum 5).
> - Do not copy the general definitions from the glossary.
> - Instead, contextualize each driver based on the specific problem. For each driver, clearly
>   state the specific conditions that should be satisfied for this decision to be considered
>   successful.

- **[DRIVER1]**: [...CRITERIA...]
- **[DRIVER2]**: [...CRITERIA...]

---

## Considered Options

> [!check]
> - Assign a short and descriptive title to each option, to serve as label should for reference
>   throughout the document.
> - Provide a brief description of the option. Focus on determinant characteristics which
>   distinguish it from the other alternatives (possibly using bullet points).
> - In this section, only include descriptive aspects (not the advantages/disadvantages/trade-offs).
> - If applicable, include a code snippet to illustrate the implementation approach. Ensure the code
>   is minimal yet representative of the option's key concept. Be consistent across the different
>   options, i.e. implement the same functionality or logic.

1. **[OPTION1]**
  [...DESCRIPTION...]
  - [...ASPECT1...]
  - [...ASPECT2...]

```python
# CODE EXAMPLE
```

2. **[OPTION2]**
  [...DESCRIPTION...]
  - [...ASPECT1...]
  - [...ASPECT2...]

---

## Analysis of Options


### Individual Assessment

> [!check]
> - For each option, refer to the decision drivers that are satisfied or unsatisfied by the option,
>   and briefly explain why and how.
> - Do not repeat the full list of decision drivers for every option if not necessary. Instead,
>   focus on those that are discriminant (i.e., those that strongly favor or disfavor the option).
> - Optionally, list additional advantages or disadvantages beyond the core decision drivers, but
>   only if they are relevant to the choice.

1. **[OPTION1]**
* Pros:
  - [SATISFIED-DRIVER]: [...WHY/HOW...]
  - Additional advantage: [...DETAILS...]
* Cons:
  - [UNSATIFIED-DRIVER]: [...WHY/HOW...]
  - Additional disadvantage: [...DETAILS...]

2. **[OPTION2]**
* Pros:
  - [SATISFIED-DRIVER]: [...WHY/HOW...]
  - Additional advantage: [...DETAILS...]
* Cons:
  - [UNSATIFIED-DRIVER]: [...WHY/HOW...]
  - Additional disadvantage: [...DETAILS...]


### Summary: Comparison by Criteria

> [!check]
> - For each key driver, assign a qualitative score to each option (high / medium / low). If a more
>   nuanced scale is needed, define it explicitly.
> - After each score, briefly mention technical keywords characteristics which recall the reasons
>   behind the assessment (e.g., "abstract classes", "inheritance", "composition"...).
> - Avoid redundant explanations. The purpose of this section is to summarize, not repeat the full
>   analysis.

- **[DRIVER1]**
  - **[OOPTION1]**: [HIGH | MEDIUM | LOW] ([KEYWORDS])
  - **[OPTION2]**: [HIGH | MEDIUM | LOW] ([KEYWORDS])

- **[DRIVER2]**
  - **[OPTION1]**: [HIGH | MEDIUM | LOW] ([KEYWORDS])
  - **[OPTION2]**: [HIGH | MEDIUM | LOW] ([KEYWORDS])

---

## Conclusions

> [!check]
> - Select the most suitable option based on the analysis.
> - State the primary reason for the final decision. Avoid generic statements. This justification
>   should clearly reflect the determinant property that was prioritized.
> - Optionally, list discarded options with a single compelling reason for rejection.
> - Finally, provide answers to the question(s) formulated in the Problem Statement section. Ensure
>   these answers directly address the problem without unnecessary elaboration.


### Decision

**Chosen option**: [OPTIONX]

**Justification**: [...DETERMINANT-REASON...]

**Discarded options** (optional):
- **[OPTIONY]**: [...REASON...]
- **[OPTIONZ]**: [...REASON...]


### Final Answers

1. [QUESTION1]
   [...ANSWER1...]
2. [QUESTION2]:
   [...ANSWER2...]

---

## Implications

> [!check]
> - Identify specific adjustments needed in the existing codebase that emerge from the decision
>   (e.g. simplifications, refactorings, abstractions).
> - Outline future constraints or requirements that this decision introduces (e.g. new features
>   required, new dependencies, new design patterns).
> - Highlight any new challenges or questions that need to be addressed.
> - If applicable, provide a high-level implementation roadmap listing steps to follow in order to
>   implement the decision or resolve new issues.
> - Among the suggested implications above, only include points that are strongly tied to the
>   decision and necessary.

- **[IMPLICATION1]**: [...DESCRIPTION...]
- **[IMPLICATION2]**: [...DESCRIPTION...]

---

## See Also

### Related Decisions

> [!check]
> - Reference related ADRs to maintain a focused and meaningful relationship between decisions.
> - Indicate the nature of the relationship (e.g., "Supersedes," "Extends," "Refines," or "Relates to").
> - If no related decisions exist, remove this section or leave it empty.

- [ADR-00YY](./00YY-example.md): [RELATION]

### References and Resources

> [!check]
> - Mention external resources, discussions or documentation that provide technical justification or
>   further insights into the decision (maximum 3 links).
> - Prioritize high-quality, authoritative sources (e.g., academic papers, well-established
>   engineering blogs, official documentation).
> - If no relevant links exist, remove this section rather than leaving it empty.

- [LINK1](URL)
- [LINK2](URL)

---

> [!info]
> **GLOSSARY - DECISION DRIVERS**
> - **Modularity**: Code should be structured into self-contained units (functions, classes,
>   modules) that can be composed.
> - **Reusability**: Code should be generalizable and adaptable in multiple contexts (different
>   parts of the project or future projects) with minimal modification.
> - **Decoupling**: Components should have minimal dependencies on each other.
> - **Cohesion**: Related functionalities should be grouped together.
> - **Separation of Concerns (SoC)**: Different functionalities should be isolated and distributed
>   across distinct components.
> - **Single Responsibility Principle (SRP)**: Each component should carry out a specific,
>   clearly-defined task.
> - **Consistency**: Components should adhere to a uniform structure and predictable behavior across
>   the project.
> - **Complexity**: Code should remain as lightweight as possible to achieve its purpose, limiting
>   the number of components, layers or interconnection.
> - **No Duplication (Don't Repeat Yourself, DRY)**: Redundant code should be avoided by abstracting
>   common logic into a central component.
> - **Clarity / Readability**: Code should be easy to read and understand, minimizing ambiguity in
>   purpose, logic, control flow.
> - **Explicitness**: Code should avoid implicit behaviors or hidden dependencies, making all
>   assumptions and operations clear.
> - **Style**: Code should leverage language features and idiomatic constructs to achieve a visually
>   appealing and compact syntax, reducing verbosity while maintaining expressiveness.
> - **Usability**: The API, interface, or system should be intuitive and predictable, facilitating
>   efficient interaction for developers or end users. It should be easy to use and learnable,
>   minimize errors, provide feedback.
> - **Encapsulation / Abstraction**: Implementation details should be hidden within modules or
>   classes, exposing only necessary interfaces to external components.
> - **Flexibility**: Code should be adaptable to changing requirements without significant
>   restructuring.
> - **Extensibility**: The design should allow new features and adaptations to new environments
>   without modifying core logic (e.g. achieved through Open/Closed Principle (OCP)).
> - **Maintainability**: The design should allow improvements and fixes without introducing
>   unintended side effects, for long-term sustainability.
> - **Correctness / Reliability**: Code should produce the expected outputs and fulfill pre-defined
>   requirements.
> - **Robustness**: Code should anticipate and handle errors, unexpected inputs and edge cases.
> - **Testability**: Code should be structured to facilitate automated unit testing, integration
>   testing, and debugging.
> - **Performance / Efficiency**: The implementation should be optimized for resource consumption
>   (processor time, memory space, network bandwidth), avoiding unnecessary overhead.
> - **Scalability**: The design should accommodate growth data volume, user load, or computational
>   complexity without performance degradation.
> - **Portability**: Code should run reliably across different hardware and operating system
>   environments with minimal changes.
