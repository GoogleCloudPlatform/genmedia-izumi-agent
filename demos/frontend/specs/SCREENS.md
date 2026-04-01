### Authentication

- **Login Screen:** Standard email/password login with a link to the registration page.
- **Registration Screen:** A simple form for new users to create an account.
- **Forgot Password Screen:** A way for users to reset their password.

### Main Application

- **Project Gallery Screen:**
  - This is the main screen after login.
  - It will display a list or grid of the user's projects.
  - Each project will show who it's shared with.
  - A prominent button to create a new project.
- **Project View Screen:** This is the main workspace.
  - **Collapsible Chat Panel (Left):** This panel will have two tabs.
    - **Chat Tab:** The primary interface for interacting with the AI agent. It supports markdown rendering, linking to canvases and assets, viewing recent chat sessions, and starting a new chat.
    - **Generate Tab:** A UI for generating assets with more control.
      - **Output Modality:** Choose from Image, Video, Music, Speech.
      - **Prompt:** A text box for the generation prompt.
      - **Reference Image:** Optional image upload for Image and Video generation.
      - **Aspect Ratio:**
        - Image: 16:9, 9:16, 3:4, 4:3, 1:1.
        - Video: 16:9, 9:16, 1:1.
      - **Resolution:**
        - Image: 1K, 2K.
        - Video: 720p, 1080p.
      - **Speech:**
        - **Voice:** A selection of different voices to use for speech generation.
  - **Main Content Area (Right):**
    - The agent can provide links to specific Canvases or Workflows in the chat. Clicking a link opens it directly.
    - **Canvas Tab:** Lists all canvases in the project. Clicking an item opens the selected canvas. A canvas is an infinite board for arranging assets.
    - **Workflow Tab:** This feature is not yet implemented. It will list all workflows in the project. A workflow is a series of connected generation steps.
    - **Assets Tab:** A gallery of all individual media assets (images, videos, etc.) generated for the project.
- **Project Sharing Modal:**
  - A modal where users can invite collaborators to a project by email.
- **User Settings Screen:**
  - For managing user account details like name, email, and password.
- **Asset Modal:**
  - View individual assets (image, video, audio).
  - Navigate between assets.
