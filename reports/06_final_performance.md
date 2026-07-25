# 06 – Final Performance Evaluation

## Objective

This report describes the methodology used to evaluate the HomeBoot Retrieval-Augmented Generation (RAG) chatbot. The evaluation measures how accurately the chatbot retrieves relevant appliance documentation and generates helpful responses for customer support queries.

## Evaluation Dataset

The chatbot will be evaluated using the Golden Evaluation Dataset consisting of **50 customer support questions** covering Whirlpool and GE washers, refrigerators, dishwashers, and dryers.

## Evaluation Metrics

The following metrics will be recorded during evaluation.

| Metric | Description | Target |
|--------|-------------|-------:|
| Retrieval Accuracy | Correct documentation retrieved | ≥ 90% |
| Response Accuracy | Correct answer generated | ≥ 90% |
| Brand Accuracy | Correct appliance brand identified | 100% |
| Category Accuracy | Correct appliance category identified | ≥ 95% |
| Source Relevance | Relevant supporting document retrieved | ≥ 90% |
| Average Response Time | Time to generate a response | < 3 seconds |

## Evaluation Workflow

The evaluation process consists of the following steps:

1. Load the Golden Evaluation Dataset.
2. Submit each customer question to the chatbot.
3. Record the retrieved documents.
4. Record the generated response.
5. Measure the response time.
6. Compare the response with the expected results.
7. Store all observations in `evaluation_results.csv`.

## Expected Outputs

The evaluation will produce:

- Retrieval Accuracy
- Response Accuracy
- Brand Accuracy
- Category Accuracy
- Average Response Time
- Overall Performance Summary

## Future Work

Once the chatbot backend is fully implemented, the evaluation pipeline will be executed to generate quantitative performance metrics. These results will be added to this report along with observations and recommendations for future improvements.