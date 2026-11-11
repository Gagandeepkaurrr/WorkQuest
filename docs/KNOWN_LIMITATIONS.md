# Known limitations

Implementation is in progress. A release claim requires the checklist evidence.
External provider, SMTP, TLS, backup target and deployment have not been tested.
Single-host Compose is not highly available. A worker failure after a provider response can cause an additional paid call; fencing prevents duplicate publication, not exactly-once billing.
