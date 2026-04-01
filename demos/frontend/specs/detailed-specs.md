# Detailed Application Specifications

This document provides a detailed breakdown of each screen and its functionalities within the Izumi Studio application.

## 1. Authentication

### 1.1. Login Screen (`/login`)

- **Purpose:** Allows existing users to sign in to the application.
- **Components:**
  - Email address field.
  - Password field.
  - "Sign In" button.
  - Link to the "Forgot Password" screen.
  - Link to the "Registration" screen.
- **Functionality:**
  - Upon successful authentication, the user is redirected to the "Project Gallery" screen (`/projects`).
  - Input validation for email format.

### 1.2. Registration Screen (`/register`)

- **Purpose:** Allows new users to create an account.
- **Components:**
  - Email address field.
  - Password field.
  - Confirm Password field.
  - "Sign Up" button.
  - Link to the "Login" screen.
- **Functionality:**
  - Validates that the password and confirm password fields match.
  - Upon successful registration, the user is likely redirected to the "Login" screen or directly into the application.
  - Input validation for email format.

### 1.3. Forgot Password Screen (`/forgot-password`)

- **Purpose:** Allows users who have forgotten their password to initiate a password reset process.
- **Components:**
  - Email address field.
  - "Reset Password" button.
  - Link to the "Login" screen.
- **Functionality:**
  - Accepts an email address and (presumably) sends a password reset link to that email.

## 2. Main Application

### 2.1. Project Gallery Screen (`/projects`)

- **Purpose:** The main landing page after a user logs in. It displays all projects associated with the user.
- **Components:**
  - **Top App Bar:** Contains the application logo/name and a user profile menu.
    - **User Profile Menu:**
      - "Settings" link to the User Settings page.
      - "Logout" button.
  - **"New Project" Button:** Opens the "New Project Modal".
  - **Project Grid:** A grid of cards, each representing a project.
    - **Project Card:**
      - Displays the project name.
      - Displays avatars of users the project is shared with.
      - Clicking the card navigates to the "Project View" screen for that project.
- **Functionality:**
  - Fetches and displays a list of projects for the current user.
  - Allows creation of new projects.
  - Provides navigation to individual projects.

### 2.2. Project View Screen (`/project/[id]`)

- **Purpose:** The main workspace for a single project, where users can interact with the AI, manage assets, and view canvases.
- **Layout:** A two-panel layout with a collapsible left panel (Chat Panel) and a main content area on the right.
- **Components:**
  - **Top App Bar:** Same as the Project Gallery screen.
  - **"Share" Button:** Opens the "Share Project Modal".
  - **Chat Panel (Left, Collapsible):**
    - **Header:**
      - Back button to navigate to the Project Gallery.
      - Editable project name.
      - Collapse/Expand button.
    - **Tabs:**
      - **Chat Tab:**
        - **New Chat View:**
          - Prompt to start a new chat.
          - Input field for the first message.
          - Lists recent chat sessions to resume from.
        - **Active Chat View:**
          - "New Chat" button to clear the session and start over.
          - Displays the message history of the current chat session.
          - Messages from the user and the AI ("Izumi") are displayed differently.
          - Supports Markdown rendering in chat messages.
          - AI messages can contain links to project assets or canvases.
          - Input field for sending new messages.
      - **Generate Tab:**
        - **Output Modality Selection:** Buttons to select between "Image", "Video", "Music", and "Speech".
        - **Common Controls:**
          - A multi-line "Prompt" text field.
        - **Image Generation Options:**
          - Reference Image Upload (up to 4).
          - Aspect Ratio selection (16:9, 9:16, 3:4, 4:3, 1:1).
          - Resolution selection (1K, 2K).
        - **Video Generation Options:**
          - Initial Frame and Last Frame image uploads.
          - Aspect Ratio selection (16:9, 9:16).
          - Resolution selection (720p, 1080p).
        - **Speech Generation Options:**
          - Voice selection dropdown.
        - **"Generate" Button:** Starts the asset generation process.
  - **Main Content Area (Right):**
    - **Tabs:**
      - **Assets Tab:**
        - Displays a grid of all assets (images, videos, audio) in the project.
        - If no assets exist, it shows a prompt to generate them.
        - Clicking an asset opens the "Asset Modal".
      - **Canvas Tab:**
        - Displays a grid of all canvases in the project.
        - If no canvases exist, it shows a message.
        - Clicking a canvas opens it in an iframe within the main content area.
      - **Workflow Tab:**
        - A placeholder for a future feature. Displays a "No workflow yet" message.

## 3. Modals

### 3.1. New Project Modal

- **Purpose:** To create a new project.
- **Triggered by:** Clicking the "New Project" button on the "Project Gallery" screen.
- **Components:**
  - Project Name text field.
  - "Create" button (disabled until a name is entered).
  - "Cancel" button.
- **Functionality:**
  - Takes a project name as input.
  - On creation, it makes an API call to create the new project and then refreshes the project list on the gallery screen.

### 3.2. Share Project Modal

- **Purpose:** To manage who has access to a project and their roles.
- **Triggered by:** Clicking the "Share" button on the "Project View" screen.
- **Components:**
  - Input field to add users by email.
  - "Add" button.
  - List of users currently shared with the project.
    - Each list item shows the user's avatar, name, and email.
    - A dropdown to change the user's role ("Editor" or "Viewer").
    - A "Remove" button to revoke access.
  - "Save" button (disabled if no changes have been made).
  - "Cancel" button.
- **Functionality:**
  - Allows project editors to add or remove users and change their roles.
  - Users with the "Viewer" role can see the sharing settings but cannot make changes.
  - Makes an API call to save the updated list of shared users.

### 3.3. Asset Modal

- **Purpose:** To view a single asset in a larger, focused view.
- **Triggered by:** Clicking on an asset in the "Assets Tab" of the "Project View" screen.
- **Components:**
  - Displays the selected asset (image, video player, or audio player).
  - "Close" button.
  - "Previous" and "Next" buttons to navigate through the project's assets.
  - A counter indicating the current asset's position in the gallery (e.g., "5 / 32").
- **Functionality:**
  - Supports keyboard navigation (left/right arrow keys) to move between assets.
  - Video and audio assets will autoplay when the modal is opened.
  - Pauses media playback when the modal is closed.

## 4. User Settings Screen (`/settings`)

- **Purpose:** Allows the user to manage their own account information.
- **Components:**
  - Name field.
  - Email address field.
  - New Password field.
  - "Save" button.
- **Functionality:**
  - Allows the user to update their name, email, and password.
  - (Presumably) makes an API call to save the updated user information.
