# Static Files Organization

This directory contains all static assets for the Color Prediction Game project.

## Directory Structure

### 📁 **css/** - Stylesheets
- `main.css` - Main stylesheet with modern design system
  - CSS variables for consistent theming
  - Responsive design components
  - Game-specific styling
  - Admin panel styling
  - Modern UI components

### 📁 **js/** - JavaScript Files
- `main.js` - Main JavaScript framework
  - UI enhancements and animations
  - WebSocket handling
  - Game logic
  - Admin panel functionality
  - Modern ES6+ features

## File Organization Guidelines

### CSS Structure
- Use CSS variables for consistent theming
- Organize styles by component/section
- Include responsive breakpoints
- Maintain consistent naming conventions

### JavaScript Structure
- Use modern ES6+ syntax
- Organize code into classes and modules
- Include proper error handling
- Document complex functions

### Asset Management
- Keep file sizes optimized
- Use appropriate image formats
- Implement caching strategies
- Maintain version control for updates

## Development Guidelines

### Adding New Styles
1. Use existing CSS variables when possible
2. Follow BEM naming convention
3. Test across different screen sizes
4. Maintain consistency with design system

### Adding New JavaScript
1. Follow existing code structure
2. Use proper error handling
3. Document new functions
4. Test functionality thoroughly

### Performance Considerations
- Minimize file sizes
- Use efficient selectors
- Optimize images and assets
- Implement proper caching headers

## File Naming Conventions

### CSS Files
- Use descriptive names: `component-name.css`
- Separate concerns: `layout.css`, `components.css`
- Use lowercase with hyphens

### JavaScript Files
- Use descriptive names: `feature-name.js`
- Group related functionality
- Use camelCase for variables and functions

## Browser Compatibility

### Supported Browsers
- Chrome 80+
- Firefox 75+
- Safari 13+
- Edge 80+

### Fallbacks
- CSS Grid with Flexbox fallback
- Modern JavaScript with polyfills
- Progressive enhancement approach
