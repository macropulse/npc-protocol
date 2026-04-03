# SwiftDeploy — NPC Protocol Case Study

[SwiftDeploy](https://swiftdeploy.ai) is a cloud infrastructure deployment service that independently converged on the NPC Protocol pattern before the spec was written. It is used here as the production reference implementation to demonstrate what a real-world NPC looks like at scale.

---

## NPC Card

```json
{
  "npc_protocol_version": "0.1.0",
  "name": "SwiftDeploy",
  "version": "1.5.0",
  "domain": "cloud infrastructure deployment and management on AWS",
  "description": "Deploys, manages, and decommissions cloud infrastructure. Handles ECS, RDS, Redis, S3, ACM, Route53, and related services via OpenTofu (Terraform-compatible). Maintains project memory across sessions.",
  "instruction_interface": "natural_language",
  "capability_opacity": "opaque",
  "session_model": "persistent",
  "confirmation_gates": [
    {
      "id": "production_deploy",
      "level": "required",
      "description": "Deploying to a production environment (affects live traffic)"
    },
    {
      "id": "decommission",
      "level": "destructive",
      "description": "Destroying all infrastructure for an environment, including stateful resources"
    }
  ],
  "pricing_hints": {
    "model": "credits",
    "unit": "session",
    "approximate_cost": "10-50 credits"
  },
  "contact": "https://swiftdeploy.ai",
  "mcp_tools": ["execute", "get_status", "write_memory", "cancel_deployment"]
}
```

Note that SwiftDeploy exposes additional tools beyond `execute` (`get_status`, `write_memory`, `cancel_deployment`). This is valid — the spec requires `execute` for natural language instructions but does not restrict additional tools.

---

## Interaction Trace: Full Deployment Flow

This is a real interaction trace showing the NPC Protocol primitives in action.

### Step 1: Calling agent reads the NPC Card

```
GET npc://card
--> NPC Card JSON (above)
```

The calling agent now knows: domain is cloud infrastructure, session is persistent, two confirmation gates exist (production_deploy: required, decommission: destructive).

### Step 2: Initial instruction

```
execute(instruction="deploy my app to staging with mysql and redis")
--> {
      "type": "in_progress",
      "session_id": "sess_a1b2c3d4",
      "message": "No infrastructure found for this project. Generating infrastructure plan first...",
      "progress": { "step": "generating_infrastructure" }
    }
```

The NPC detects that no infrastructure exists yet (reads project memory) and autonomously decides to generate it before deploying. The calling agent does not need to know this — it just sees `in_progress`.

### Step 3: Polling for progress

```
get_status(project_id="...", environment="staging")
--> {
      "status": "deploying",
      "current_step": "aws_ecs_service.app: Still creating...",
      "elapsed_seconds": 87,
      "recent_logs": [...]
    }
```

### Step 4: Completion

```
get_status(project_id="...", environment="staging")
--> {
      "type": "completed",
      "session_id": "sess_a1b2c3d4",
      "result": "Staging environment deployed successfully",
      "data": {
        "app_url": "https://my-app-staging.app.swiftdeploy.ai",
        "ecr_push_command": "docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/my-app:latest"
      }
    }
```

---

## Interaction Trace: Decommission with Destructive Gate

### Step 1: Instruction

```
execute(instruction="tear down the staging environment")
--> {
      "type": "needs_confirmation",
      "session_id": "sess_x9y8z7w6",
      "gate_id": "decommission",
      "gate_level": "destructive",
      "prompt": "This will permanently destroy all infrastructure for 'my-app' in staging.",
      "protected_resources": [
        {
          "type": "aws_rds_instance",
          "name": "my-app-staging-db",
          "risk": "All database data will be permanently deleted"
        },
        {
          "type": "aws_secretsmanager_secret",
          "name": "my-app-staging-credentials",
          "risk": "Credentials will be permanently deleted"
        }
      ]
    }
```

The calling agent MUST show this full list to the human user. It cannot auto-confirm.

### Step 2: Human confirms, calling agent relays

```
execute(instruction="yes, confirmed", session_id="sess_x9y8z7w6", confirm=true)
--> {
      "type": "completed",
      "session_id": "sess_x9y8z7w6",
      "result": "Staging environment decommissioned. All resources destroyed."
    }
```

---

## Memory Architecture

SwiftDeploy uses all three memory tiers defined in the NPC Protocol session model:

| Tier | What SwiftDeploy stores |
|---|---|
| **Ephemeral** | In-flight terraform plan, intermediate reasoning steps |
| **Session** | Current deployment conversation: what was asked, what decisions were made, pending confirmations |
| **Persistent** | Project memory: AWS account ID, architecture plan, deployment history, known issues, manual changes recorded via `write_memory` |

The persistent memory is what enables the NPC to say things like "you already have an RDS instance from your last deployment — I'll reuse it" or "last time you deployed this, the Secrets Manager deletion window caused a 7-day delay — I'll handle that automatically this time."

---

## What Was Hard Without the Spec

Before NPC Protocol named these patterns, SwiftDeploy had to:

1. **Invent its own confirmation gate format** — the `needs_confirmation` / `needs_decommission_confirmation` response types were invented ad-hoc. Calling agents had to read SwiftDeploy-specific documentation to understand them.

2. **Document its session model informally** — there was no standard way to communicate "I maintain persistent project memory" to a calling agent. This was buried in the skills file.

3. **Explain `recovery_hint` as a custom convention** — the fact that every `failed` response includes a recovery hint was a SwiftDeploy design decision, not a known standard.

4. **Define capability opacity without a term for it** — SwiftDeploy's `execute` tool intentionally doesn't expose its internal tool list, but there was no standard way to declare this. Calling agents sometimes tried to enumerate tools and got confused.

NPC Protocol names all of these patterns and makes them discoverable via the NPC Card, so calling agents can handle them generically without reading NPC-specific documentation.
