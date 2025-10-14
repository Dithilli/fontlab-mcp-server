# FontLab MCP Server

A Model Context Protocol (MCP) server that provides programmatic access to FontLab's PythonQt API, enabling Claude and other AI assistants to interact with FontLab for font design and manipulation.

## Overview

This MCP server bridges the Model Context Protocol with FontLab's powerful font editing capabilities, allowing you to:

- Query font metadata and glyph information
- Create and modify glyphs programmatically
- Apply transformations (scale, rotate, translate)
- Export fonts to various formats
- Automate font design workflows

## Architecture

```
┌─────────────────┐
│   Claude/MCP    │
│     Client      │
└────────┬────────┘
         │ MCP Protocol (stdio)
         │
┌────────▼────────┐
│  FontLab MCP    │
│     Server      │
│  (Python)       │
└────────┬────────┘
         │ Script Execution
         │
┌────────▼────────┐
│    FontLab      │
│   Application   │
│  (PythonQt API) │
└─────────────────┘
```

The server uses a bridge pattern to execute Python scripts within FontLab's environment, communicating via temporary files and JSON serialization.

## Features

### Resources (Read-Only Operations)

- `fontlab://font/current` - Get current font information
- `fontlab://font/current/glyphs` - List all glyphs
- `fontlab://font/info` - Get detailed font metadata
- `fontlab://glyph/{name}` - Get specific glyph details

### Tools (Write Operations)

- `create_glyph` - Create new glyphs with custom parameters
- `modify_glyph_width` - Adjust glyph widths
- `transform_glyph` - Apply scale, rotation, and translation
- `update_font_info` - Modify font metadata
- `export_font` - Export to OTF, TTF, WOFF, WOFF2, UFO
- `delete_glyph` - Remove glyphs from font

## Installation

### Prerequisites

- Python 3.10 or higher
- FontLab 7 or 8 installed
- `pip` package manager

### Setup

1. Clone this repository:
   ```bash
   git clone https://github.com/dithilli/fontlab-mcp-server.git
   cd fontlab-mcp-server
   ```

2. Create a virtual environment (recommended):
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Install the package:
   ```bash
   pip install -e .
   ```

### Configuration

The server automatically detects FontLab installations in standard locations:
- macOS: `/Applications/FontLab 8.app` or `/Applications/FontLab 7.app`
- Custom paths can be configured in the bridge initialization

## Usage

### Running the Server

Start the server using stdio transport:

```bash
python -m src.server
```

Or use the installed command:

```bash
fontlab-mcp-server
```

### Claude Desktop Configuration

Add to your Claude Desktop config file (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "fontlab": {
      "command": "/path/to/venv/bin/python",
      "args": ["-m", "src.server"],
      "cwd": "/path/to/fontlab-mcp-server"
    }
  }
}
```

### Example Usage with Claude

Once configured, you can ask Claude to:

**Query font information:**
> "What fonts are currently open in FontLab?"

**Create glyphs:**
> "Create a new glyph called 'customA' with a width of 650"

**Modify glyphs:**
> "Scale the 'A' glyph by 1.2x horizontally"

**Export fonts:**
> "Export the current font as an OTF to ~/Desktop/myfont.otf"

## API Reference

### Resources

#### Get Current Font
```
URI: fontlab://font/current
Returns: JSON with font metadata
```

#### List Glyphs
```
URI: fontlab://font/current/glyphs
Returns: Array of glyph objects with names, unicodes, and widths
```

#### Get Glyph Details
```
URI: fontlab://glyph/{name}
Parameters:
  - name: Glyph name (e.g., "A", "space", "Agrave")
Returns: Detailed glyph information including bounds and contours
```

### Tools

#### create_glyph
```json
{
  "name": "glyph_name",
  "unicode": 65,  // optional
  "width": 600    // optional, default 600
}
```

#### modify_glyph_width
```json
{
  "name": "glyph_name",
  "width": 650
}
```

#### transform_glyph
```json
{
  "name": "glyph_name",
  "scale_x": 1.2,      // optional, default 1.0
  "scale_y": 1.0,      // optional, default 1.0
  "rotate": 45,        // optional, default 0 (degrees)
  "translate_x": 10,   // optional, default 0
  "translate_y": 0     // optional, default 0
}
```

#### update_font_info
```json
{
  "family_name": "My Font Family",  // optional
  "style_name": "Bold",             // optional
  "version": "1.0",                 // optional
  "copyright": "Copyright 2025"     // optional
}
```

#### export_font
```json
{
  "path": "/path/to/output.otf",
  "format": "otf"  // optional: otf, ttf, woff, woff2, ufo
}
```

#### delete_glyph
```json
{
  "name": "glyph_name"
}
```

## Development

### Project Structure

```
fontlab-mcp-server/
├── src/
│   ├── __init__.py           # Package initialization
│   ├── server.py             # Main MCP server
│   ├── fontlab_bridge.py     # FontLab communication bridge
│   ├── resources.py          # Resource handlers
│   ├── tools.py              # Tool handlers
│   └── utils/                # Utility functions
├── scripts/                  # FontLab executor scripts
├── tests/                    # Unit tests
├── pyproject.toml            # Package configuration
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

### Testing

Run tests:
```bash
pytest tests/
```

### Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Limitations & Notes

- FontLab must be running for the server to function
- Script execution uses subprocess communication, which may have latency
- Some FontLab features may require specific versions (7 or 8)
- The bridge assumes FontLab CLI accepts `-script` flag (may need adjustment)

## Roadmap

Future enhancements:

- [ ] Support for component manipulation
- [ ] Kerning table operations
- [ ] OpenType feature editing
- [ ] Batch glyph operations
- [ ] Real-time event streaming
- [ ] Better error handling and validation
- [ ] Support for multiple open fonts
- [ ] Undo/redo functionality

## License

MIT License - See [LICENSE](LICENSE) file for details

## Acknowledgments

- Built on [Anthropic's Model Context Protocol](https://modelcontextprotocol.io/)
- Integrates with [FontLab's Python API](https://fontlabcom.github.io/fontlab-python-docs/)

## Support

For issues, questions, or contributions, please visit:
- GitHub: [https://github.com/dithilli/fontlab-mcp-server](https://github.com/dithilli/fontlab-mcp-server)
- FontLab API Docs: [https://fontlabcom.github.io/fontlab-python-docs/](https://fontlabcom.github.io/fontlab-python-docs/)

---

**Version:** 0.1.0
**Author:** David Szarzynski
**Status:** Alpha - MVP Implementation
