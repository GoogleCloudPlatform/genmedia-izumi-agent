# Testing Strategy

This document outlines the strategy for implementing tests for the application logic.

## 1. Frameworks and Tools

- **Test Runner**: [Vitest](https://vitest.dev/) will be used as the test runner. It's fast, compatible with Vite, and has a Jest-compatible API.
- **Test Environment**: `jsdom` will be used as the default browser-like environment for running React component tests within Node.js. This provides a simulated DOM for components to render and interact with.
- **Component Testing**: [React Testing Library](https://testing-library.com/docs/react-testing-library/intro/) will be used for rendering and interacting with React components in a way that resembles a user.
- **User Interactions**: `@testing-library/user-event` will be used to simulate user events like typing and clicking.
- **Network Mocking**: [MSW (Mock Service Worker)](https://mswjs.io/) will be adopted for mocking API calls. This allows interception of network requests at a lower level, providing a more realistic mocking experience that can be shared across unit tests (Vitest) and even during local development in the browser. This is preferred over directly mocking `fetch` or `axios` in individual tests for better reusability and consistency.
- **Assertions**: Vitest's built-in `expect` will be used for assertions, along with custom matchers from `@testing-library/jest-dom`.

## 2. Unit Tests for Services

Unit tests for services will focus on business logic, ensuring that data is transformed, cached, and managed correctly. The API layer (`src/services/api`) will be mocked using MSW where network requests are involved, and `vi.mock` for internal dependencies.

### `projectService.ts`

- **`getProjects`**:
  - It should fetch projects from the database and return them sorted by `lastAccessedAt` in descending order.
  - It should correctly filter for `active` and `archived` projects.
- **`createProject`**:
  - It should call the `api.createProject` function with the correct name.
- **`getProjectById`**:
  - It should fetch project info, assets, canvases, and chat sessions in parallel.
  - It should return a composite project object with all the fetched data.
  - It should use cached data if `forceRefresh` is false.
  - It should re-fetch data if `forceRefresh` is true.

### `chatService.ts`

- **`sendMessage`**:
  - It should correctly handle SSE messages, distinguishing between `partial` and `non-partial` events.
  - It should accumulate text from `partial` messages into a single message.
  - It should trigger the `onPartialUpdate` callback with `isFinal: true` for non-partial messages (signaling completion of an agent action).
  - It should correctly update the message cache with user and agent messages.
- **`getChatSessionMessages`**:
  - It should return cached messages if `forceRefresh` is false.
  - It should fetch messages from the API if `forceRefresh` is true or if the cache is empty.

### `mediaService.ts`

- **`checkJobStatus`**:
  - It should correctly poll for job statuses and categorize them into `active`, `completed`, and `failed`.
  - It should handle API errors gracefully and keep the job in the pending list.
- **`generate...` functions**:
  - They should call the corresponding `api.generate...` function.
  - They should add the newly created job to the `pendingJobs` list.

## 3. Component Tests

Component tests will focus on user interactions and rendering logic. Services and API calls will be mocked using MSW and `vi.mock` to provide controlled data and verify that the components call the correct functions and display expected states.

### `NewProjectModal.tsx`

- It should call `onCreate` with the project name when the "Create" button is clicked.
- The "Create" button should be disabled if the project name is empty.
- It should call `onClose` when the "Cancel" button is clicked.

### `ProjectGrid.tsx`

- It should display a list of projects fetched from the `projectService`.
- It should filter the displayed projects when the user types in the filter text field.
- It should navigate to the project page when a project card is clicked.
- It should open the `NewProjectModal` when the "New Project" button is clicked.
- It should correctly handle archiving, unarchiving, renaming, and deleting projects via menu actions.

### `ChatInterface.tsx`

- It should display the `ChatSessionList` when no `chatSessionId` is provided.
- It should display the `ActiveConversation` when a `chatSessionId` is provided.
- It should correctly handle the creation of a new chat session and navigate to it.
- It should display a loading spinner while fetching sessions or creating a new one.

### `ActiveConversation.tsx`

- It should display the chat messages for the current session.
- It should send the `autoGreeting` message silently when a new session starts.
- It should call `chatService.sendMessage` with the correct message and files when the user sends a message.
- It should display a "thinking" indicator while waiting for the agent's response.
- It should correctly trigger the `onRefreshProject` callback when a non-partial message is received from the agent (e.g., after a tool call).
- It should handle optimistic UI updates and revert them on error.

### `GenerateInterface.tsx`

- It should preserve the form state for each modality (image, video, music, speech) when switching between tabs.
- It should call the correct `mediaService.generate...` function with the current form data when the "Generate" button is clicked.
- The "Generate" button should be disabled if the prompt for the active modality is empty.
- It should display an error message if the generation job fails to initiate.

## 5. End-to-End Tests (Future)

While not in the immediate scope, end-to-end tests should be added in the future to simulate user workflows from start to finish. This will provide the highest level of confidence that the application is working as expected.

Key workflows to test:

- **Project Creation**: A user creates a new project and is navigated to the project page, verifying the URL and initial content.
- **Chat Interaction**: A user starts a new chat, sends a message (with/without attachments), receives a response from the agent (including intermediate steps), and sees related assets/canvases updated if applicable.
- **Media Generation**: A user navigates to the generation tab, fills out a form for a specific modality, triggers generation, and observes the pending job in the assets view, eventually seeing the completed asset.
- **Project Management**: A user archives, unarchives, renames, and deletes a project, verifying the list updates accordingly.
