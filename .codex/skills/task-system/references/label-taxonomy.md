# Label Taxonomy

## Type

- `type:feat`
- `type:fix`
- `type:docs`
- `type:test`
- `type:chore`
- `type:refactor`
- `type:design`
- `type:infra`

## Kind

- `kind:umbrella`
- `kind:leaf`
- `kind:standalone`
- `kind:risk-management`
- `kind:risk-resolution`
- `kind:decision`
- `kind:spike`

## Status

- `status:idea`
- `status:intake`
- `status:ready`
- `status:in-progress`
- `status:blocked`
- `status:review`
- `status:done`

## Priority

- `priority:p0`
- `priority:p1`
- `priority:p2`
- `priority:p3`

## Area

- `area:ops`
- `area:docs`
- `area:audio`
- `area:stt`
- `area:cli`
- `area:test`
- `area:ci`
- `area:design`

## Rules

- Exactly one `type:*`.
- Exactly one `kind:*`.
- Exactly one `status:*`.
- Exactly one `priority:*`.
- One or more `area:*`.
- Issue title prefix must match `type:*`.
