---
name: gitnexus-debugging
description: "Use when the user is debugging a bug, tracing an error, or asking why something fails. Examples: \"Why is X failing?\", \"Where does this error come from?\", \"Trace this bug\""
---

# Debugging with GitNexus

## When to Use

- "Why is this function failing?"
- "Trace where this error comes from"
- "Who calls this method?"
- "This endpoint returns 500"
- Investigating bugs, errors, or unexpected behavior

## Workflow

```
1. READ gitnexus://repos                                      → Discover indexed repos
2. READ gitnexus://repo/{name}/context                         → Check overview and staleness
3. gitnexus_query({query: "<error or symptom>", repo: "<name>"}) → Find related execution flows
4. gitnexus_context({name: "<suspect>", repo: "<name>"})        → See callers/callees/processes
5. READ gitnexus://repo/{name}/process/{processName}            → Trace execution flow
6. gitnexus_cypher({query: "MATCH path...", repo: "<name>"})    → Custom traces if needed
```

> If step 2 says "Index is stale" → run `npx gitnexus analyze` in terminal.

## Checklist

```
- [ ] Understand the symptom (error message, unexpected behavior)
- [ ] READ gitnexus://repos and choose the correct repo
- [ ] READ gitnexus://repo/{name}/context and check staleness
- [ ] gitnexus_query for error text or related code
- [ ] Identify the suspect function from returned processes
- [ ] gitnexus_context to see callers and callees
- [ ] Trace execution flow via process resource if applicable
- [ ] gitnexus_cypher for custom call chain traces if needed
- [ ] Read source files to confirm root cause
```

## Debugging Patterns

| Symptom              | GitNexus Approach                                          |
| -------------------- | ---------------------------------------------------------- |
| Error message        | `gitnexus_query` for error text → `context` on throw sites |
| Wrong return value   | `context` on the function → trace callees for data flow    |
| Intermittent failure | `context` → look for external calls, async deps            |
| Performance issue    | `context` → find symbols with many callers (hot paths)     |
| Recent regression    | `gitnexus_detect_changes` to see what your changes affect  |

## Tools

**gitnexus_query** — find code related to error:

```
gitnexus_query({
  query: "payment validation error",
  task_context: "debugging payment failure",
  goal: "find throw sites and related execution flows",
  repo: "my-app"
})
→ Processes: CheckoutFlow, ErrorHandling
→ Symbols: validatePayment, handlePaymentError, PaymentException
```

**gitnexus_context** — full context for a suspect:

```
gitnexus_context({name: "validatePayment", repo: "my-app"})
→ Incoming calls: processCheckout, webhookHandler
→ Outgoing calls: verifyCard, fetchRates (external API!)
→ Processes: CheckoutFlow (step 3/7)
```

**gitnexus_cypher** — custom call chain traces:

```cypher
MATCH path = (a)-[:CodeRelation {type: 'CALLS'}*1..2]->(b:Function {name: "validatePayment"})
RETURN [n IN nodes(path) | n.name] AS chain
```

Call it with the repo name when more than one repo is indexed:

```
gitnexus_cypher({
  query: "MATCH path = (a)-[:CodeRelation {type: 'CALLS'}*1..2]->(b:Function {name: 'validatePayment'}) RETURN [n IN nodes(path) | n.name] AS chain",
  repo: "my-app"
})
```

## Example: "Payment endpoint returns 500 intermittently"

```
1. READ gitnexus://repo/my-app/context
   → 918 symbols, 45 processes, index fresh

2. gitnexus_query({query: "payment error handling", repo: "my-app"})
   → Processes: CheckoutFlow, ErrorHandling
   → Symbols: validatePayment, handlePaymentError

3. gitnexus_context({name: "validatePayment", repo: "my-app"})
   → Outgoing calls: verifyCard, fetchRates (external API!)

4. READ gitnexus://repo/my-app/process/CheckoutFlow
   → Step 3: validatePayment → calls fetchRates (external)

5. Root cause: fetchRates calls external API without proper timeout
```
