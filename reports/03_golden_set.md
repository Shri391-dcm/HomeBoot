# Golden Evaluation Set

## Purpose

This document defines the evaluation dataset used to assess the performance of the Home Appliance AI Support Assistant. The golden set consists of representative user questions and their expected answers based on official Whirlpool and GE Appliances documentation.

The purpose of this evaluation is to verify that the chatbot retrieves relevant information, generates accurate responses, cites appropriate sources, and avoids providing unsupported information.

---

## Evaluation Criteria

Each response will be evaluated using the following criteria:

- Retrieval Accuracy
- Answer Correctness
- Source Citation
- Completeness
- Hallucination Prevention

---

## Golden Test Cases

| ID | User Question | Expected Result |
|----|---------------|-----------------|
| 1 | My Whirlpool washing machine is not draining. What should I do? | Provide troubleshooting steps from Whirlpool documentation and cite the source. |
| 2 | Why is my GE refrigerator making a loud buzzing noise? | Explain common causes using official GE documentation and include citation. |
| 3 | My dishwasher leaves dishes dirty after every wash. | Recommend troubleshooting steps from the appliance manual. |
| 4 | How often should I clean my refrigerator water filter? | Return the maintenance recommendation from official documentation. |
| 5 | What does error code F21 mean on a Whirlpool washer? | Explain the error code and recommended actions using official documentation. |

---

## Success Criteria

The chatbot is considered successful when it:

- Retrieves relevant documentation.
- Produces factually correct answers.
- Includes source citations.
- Avoids fabricated information.
- Responds appropriately when information is unavailable.

---

## Future Evaluation

Additional test cases covering different appliance models and edge cases will be added as the knowledge base expands.