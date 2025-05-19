graph TD
    %% Start of the workflow
    A[Start] --> B{Load Feedback Data from JSON}

    %% Handle feedback data loading
    B -->|Success| C[For each feedback entry]
    B -->|Failure| Z[Log Error and Exit]

    %% Process each feedback entry
    C --> D[Route Feedback: Classify as Operational or Non-Operational]

    %% Decision based on routing confidence
    D -->|Confidence >= 0.7| E{Is Feedback Operational?}
    D -->|Confidence < 0.7| F[Log Warning: Low Confidence]
    F --> G[Return Failed Analysis: Confidence Too Low]

    %% Handle operational feedback
    E -->|Yes| H[Classify Operational Feedback]
    H -->|Success| I[Extract Feedback Details]
    I -->|Success| J[Generate Feedback Analysis]
    J -->|Success| K[Create JIRA Ticket]
    K --> L[Return Successful Analysis with Ticket]

    %% Handle non-operational feedback
    E -->|No| M[Log Non-Operational Feedback]
    M --> N[Return Non-Actionable Result]

    %% Error handling for classification, extraction, and analysis
    H -->|Failure| O[Return Failed Analysis: Classification Failed]
    I -->|Failure| P[Return Failed Analysis: Details Extraction Failed]
    J -->|Failure| Q[Return Failed Analysis: Analysis Generation Failed]

    %% End of processing for each feedback entry
    G --> R[End]
    L --> R[End]
    N --> R[End]
    O --> R[End]
    P --> R[End]
    Q --> R[End]
    Z --> R[End]

    %% Subgraph for operational feedback processing
    subgraph Operational Feedback Processing
        H --> I --> J --> K
    end

    %% Subgraph for non-operational feedback handling
    subgraph Non-Operational Feedback Handling
        M --> N
    end

    %% Notes for clarity
    classDef note fill:#f9f,stroke:#333,stroke-width:2px;
    T[Note: Operational feedback is routed to teams like Product, IT, or Arena Ops.]:::note
    U[Note: Non-operational feedback is logged and skipped.]:::note
    V[Note: Confidence threshold ensures reliable routing.]:::note
    W[Note: JIRA tickets are created only for operational feedback.]:::note