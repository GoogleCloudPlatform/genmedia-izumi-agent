# Gemini Agent Notes

## Development Workflow Verification

To avoid disrupting the user's `npm run dev` server, the following verification strategy will be employed:

1.  **Rely on `npm run dev` output:** For immediate feedback during development, assume `npm run dev` is running and providing real-time compilation and type-checking errors/warnings.
2.  **Use targeted checks for explicit verification:** If a more explicit check is needed without a full build, use the following commands from within the `genmedia-agent` directory:
    - `npx tsc --noEmit` (for type-checking only)
    - `npm run lint` (if a lint script is defined in `package.json`)
3.  **Reserve `npm run build` for final checks:** `npm run build` will only be used as a final verification step before suggesting a commit or for production-readiness checks, and not as a routine development verification step.

## Architecture

- Implement API calls in a service, don't use fetch directly in the UI components.

## Code Formatting

- Always run `npm run format` (which uses Prettier) to format the code before committing or pushing changes.
