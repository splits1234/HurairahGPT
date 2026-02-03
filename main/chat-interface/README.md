# HurairahGPT Chat Interface

![HurairahGPT Logo](https://via.placeholder.com/150x50?text=HurairahGPT)
[![React](https://img.shields.io/badge/React-18.x-61DAFB?style=flat-square&logo=react)](https://reactjs.org/)
[![Vite](https://img.shields.io/badge/Vite-5.x-646CFF?style=flat-square&logo=vite)](https://vitejs.dev/)
[![Framer Motion](https://img.shields.io/badge/Framer%20Motion-10.x-000000?style=flat-square&logo=framer)](https://www.framer.com/motion/)
[![ESLint](https://img.shields.io/badge/ESLint-8.x-4B32C3?style=flat-square&logo=eslint)](https://eslint.org/)

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Development](#development)
  - [Building for Production](#building-for-production)
- [Architecture](#architecture)
  - [Component Hierarchy](#component-hierarchy)
  - [State Management](#state-management)
  - [API Integration](#api-integration)
- [Customization](#customization)
  - [Themes](#themes)
  - [Personalities](#personalities)
- [Contributing](#contributing)
- [License](#license)
- [Support](#support)

---

## Overview

HurairahGPT Chat Interface is a modern, responsive React application that serves as the frontend for the HurairahGPT AI chatbot platform. Built with React 18, Vite, and Framer Motion, it provides a smooth, animated user experience with real-time chat capabilities.

The application integrates with a Flask backend to provide:
- AI-powered chat conversations
- Multiple chat sessions management
- Image generation (via API)
- Theme customization (dark/light mode)
- AI personality selection

---

## Features

### Core Features
- 💬 **Real-time Chat** - Instant messaging interface with AI assistant
- 📱 **Responsive Design** - Works seamlessly on desktop and mobile devices
- 🌙 **Dark/Light Theme** - Toggle between themes with smooth transitions
- 👥 **Multiple Sessions** - Create, switch, and manage multiple chat sessions
- 🎨 **AI Personalities** - Choose from different AI conversation styles
- 📤 **Export Chat** - Download conversation history as text files
- 🔍 **Session Search** - Find previous conversations quickly

### Technical Features
- ⚡ **Fast Performance** - Powered by Vite for lightning-fast builds
- 🎯 **Type Safety** - Comprehensive TypeScript-like documentation
- ♿ **Accessibility** - ARIA labels and keyboard navigation support
- 🔄 **State Persistence** - Theme and session data saved to localStorage
- 🎬 **Smooth Animations** - Framer Motion powered micro-interactions

---

## Project Structure

```
chat-interface/
├── public/
│   └── vite.svg                 # Vite logo
├── src/
│   ├── assets/
│   │   └── react.svg            # React logo
│   ├── components/
│   │   ├── InputBar.jsx         # Message input component
│   │   ├── InputBar.module.css  # Input styles
│   │   ├── Sidebar.jsx          # Session sidebar component
│   │   ├── Sidebar.module.css   # Sidebar styles
│   │   ├── ThemeToggle.jsx      # Theme switcher button
│   │   └── ThemeToggle.module.css
│   ├── hooks/
│   │   └── useTheme.js          # Theme management hook
│   ├── styles/
│   │   ├── global.css           # Global styles
│   │   └── variables.css        # CSS variables
│   ├── App.css                  # App component styles
│   ├── App.jsx                  # Main application component
│   ├── App.module.css           # App component styles (module)
│   ├── index.css                # Index styles
│   └── main.jsx                 # Application entry point
├── .gitignore
├── eslint.config.js             # ESLint configuration
├── index.html                   # HTML template
├── package.json                 # Project dependencies
├── package-lock.json            # Locked dependency versions
├── README.md                    # This file
└── vite.config.js               # Vite configuration
```

---

## Getting Started

### Prerequisites

Before you begin, ensure you have the following installed:

- **Node.js** (version 18 or higher) - [Download](https://nodejs.org/)
- **npm** (comes with Node.js) or **yarn** - [Download yarn](https://yarnpkg.com/)
- A modern web browser (Chrome, Firefox, Safari, Edge)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/hurairahgpt.git
   cd hurairahgpt/main/chat-interface
   ```

2. **Install dependencies**
   ```bash
   # Using npm
   npm install
   
   # OR using yarn
   yarn install
   ```

3. **Configure environment variables**
   
   Create a `.env` file in the chat-interface directory:
   ```env
   VITE_API_URL=http://localhost:5000
   VITE_APP_NAME=HurairahGPT
   ```

### Development

Start the development server:

```bash
# Using npm
npm run dev

# OR using yarn
yarn dev
```

The application will be available at `http://localhost:5173`

**Development Features:**
- Hot Module Replacement (HMR)
- Fast refresh for React components
- Source maps for debugging
- ESLint integration

### Building for Production

Build the application for production deployment:

```bash
# Using npm
npm run build

# OR using yarn
yarn build
```

The built files will be in the `dist/` directory, ready for deployment to any static hosting service.

---

## Architecture

### Component Hierarchy

```
App
├── Sidebar
│   ├── ThemeToggle
│   └── User Profile Section
├── Main Canvas
│   ├── Top Toolbar
│   │   ├── Personality Select
│   │   ├── Export Button
│   │   └── Clear Chat Button
│   ├── Content Wrapper
│   │   ├── Logo (when no messages)
│   │   └── Chat History (when messages exist)
│   └── InputBar
```

### State Management

The application uses React's built-in state management:

| State | Type | Purpose |
|-------|------|---------|
| `isLoading` | boolean | Controls loading screen visibility |
| `user` | object | User profile and preferences |
| `sessions` | object | Dictionary of all chat sessions |
| `activeSessionId` | string | Currently selected session |
| `chatHistory` | array | Messages in current session |
| `personality` | string | Selected AI personality |
| `isSidebarVisible` | boolean | Mobile sidebar toggle |

### API Integration

The frontend communicates with the Flask backend via REST API:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/init` | GET | Initialize app with user data |
| `/chat` | POST | Send message, get AI response |
| `/sessions/create` | POST | Create new chat session |
| `/sessions/switch` | POST | Switch to different session |
| `/sessions/delete` | POST | Delete a session |
| `/sessions/rename` | POST | Rename a session |
| `/api/generate_title` | POST | Generate session title with AI |
| `/image` | POST | Generate image from prompt |
| `/image/check-limit` | GET | Check image generation quota |
| `/personality` | POST | Update AI personality |
| `/theme` | POST | Update theme preference |
| `/logout` | GET | Log out user |

---

## Customization

### Themes

The application supports two themes:

| Theme | Description |
|-------|-------------|
| `dark` | Dark background with light text (default) |
| `light` | Light background with dark text |

**CSS Variables** (defined in `src/styles/variables.css`):
```css
:root {
  --bg-primary: #1a1a2e;
  --bg-secondary: #16213e;
  --text-primary: #ffffff;
  --text-secondary: #a0a0a0;
  --accent-color: #0f3460;
  --border-color: #e94560;
}
```

### Personalities

Four AI personalities are available:

| Personality | Description | Use Case |
|-------------|-------------|----------|
| `default` | Helpful, friendly assistant | General use |
| `funny` | Witty, sarcastic, jokes around | Entertainment |
| `islamic` | Islamic knowledge focus | Religious questions |
| `coder` | Programming expert | Technical help |

---

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

This project is proprietary software. All rights reserved.

Copyright (c) 2025 Hurairah
All Rights Reserved.

---

## Support

For support, please contact:
- **Email**: hurairahgpt.devteam@gmail.com
- **Website**: https://talktohurairah.com
- **Issues**: [GitHub Issues](https://github.com/yourusername/hurairahgpt/issues)

---

## Acknowledgments

- [React](https://reactjs.org/) - UI Library
- [Vite](https://vitejs.dev/) - Build Tool
- [Framer Motion](https://www.framer.com/motion/) - Animation Library
- [Lucide](https://lucide.dev/) - Icons
- [Flask](https://flask.palletsprojects.com/) - Backend Framework
- [OpenRouter](https://openrouter.ai/) - AI API Provider

---

<div align="center">
  Made with ❤️ by Hurairah
</div>
