# FontLab API Research & MCP Extension Plan

## Current Implementation Status

### Resources (Read-only)
- `fontlab://font/current` - Current font info
- `fontlab://font/current/glyphs` - List all glyphs
- `fontlab://font/info` - Font metadata
- `fontlab://glyph/{name}` - Individual glyph details

### Tools (Write operations)
- `create_glyph` - Create new glyph with name, unicode, width
- `modify_glyph_width` - Change glyph width
- `transform_glyph` - Scale, rotate, translate glyphs
- `update_font_info` - Update family name, style, version, copyright
- `export_font` - Export to OTF, TTF, WOFF, WOFF2, UFO
- `delete_glyph` - Remove glyphs

**Coverage: ~10% of FontLab API capabilities**

---

## FontLab Python API Overview

### Four Main Packages

1. **fontlab** - High-level GUI-integrated operations
2. **fontgate** - Low-level font engine (technical operations)
3. **typerig** - Pythonic wrapper library by Vassil Kateliev
4. **FL** - Legacy FontLab Studio 5 compatibility

### Key FontLab 8 Features
- Python 3.11 (10-60% faster than previous versions)
- 340+ preference attributes via `flPreferences`
- Action set execution via Python
- HTML rendering in output panel
- Special protocols: `glyph:`, `class:`, `file:`
- Startup script hooks: `startupScript.py`, `initScript.py`

### Core API Classes

**High-level (fontlab):**
- `flWorkspace` - Application control
- `flPackage` - Font container
- `flGlyph` - Glyph operations
- `flLayer` - Layer operations
- `flContour` - Contour representation
- `flNode` - Node operations
- `flTransform` - Geometric transformations

**Low-level (fontgate):**
- `fgFont` - Font with kerning, features, axes, guides
- `fgGlyph` - Glyph with anchors, components, contours
- `fgKerning` - Kerning pairs and classes
- `fgAnchor` / `fgAnchors` - Anchor points
- `fgComponent` / `fgComponents` - Composite glyphs
- `fgContour` / `fgContours` - Bezier paths
- `fgAxis` / `fgAxes` - Variable font axes
- `fgBitmap` - Embedded bitmaps
- `fgCoding` - Character encoding/mapping
- `fgColor` - Color support

---

## Gap Analysis - Missing Features

### 1. Kerning & Spacing (0% coverage)
- No kerning pair management
- No kerning classes
- No auto-kerning features
- No metrics classes

### 2. OpenType Features (0% coverage)
- No feature code access/modification
- No glyph classes management
- No GSUB/GPOS manipulation

### 3. Contours & Shapes (0% coverage)
- No path/contour manipulation
- No bezier curve editing
- No node operations
- No shape operations (union, intersect, etc.)

### 4. Anchors (0% coverage)
- No anchor creation/editing
- No mark positioning

### 5. Components (0% coverage)
- No composite glyph operations
- No component transformation

### 6. Variable Fonts (0% coverage)
- No axes management
- No masters manipulation
- No interpolation
- No instance generation

### 7. Guides & Alignment (0% coverage)
- No guide creation/management
- No alignment zones

### 8. Hinting (0% coverage)
- No TrueType hinting
- No PostScript hints

### 9. Advanced Glyph Operations (5% coverage)
- Basic metrics only (LSB, RSB missing)
- No tags, notes, marks
- No glyph renaming/duplication
- No glyph searching by unicode

### 10. Layers (0% coverage)
- No layer management
- No multi-master layer operations

### 11. Font-level Operations (10% coverage)
- Basic info only
- No font validation
- No glyph sorting/reordering
- No font comparison
- No batch operations

### 12. Color Fonts (0% coverage)
- No color layer management
- No SVG/COLR/CBDT support

### 13. Bitmaps (0% coverage)
- No bitmap glyph support

### 14. Import/Export (20% coverage)
- Basic export only
- No import functionality
- No format conversion options
- No UFO read/write

### 15. Application Control (0% coverage)
- No viewport manipulation
- No UI interaction
- No preferences access
- No action set execution

---

## Proposed Extensions by Category

### A. KERNING & METRICS (High Value)

**Resources:**
- `fontlab://font/kerning` - Get all kerning pairs
- `fontlab://font/kerning/classes` - Get kerning classes
- `fontlab://font/metrics-classes` - Get metrics classes

**Tools:**
- `set_kerning_pair` - Set kerning between two glyphs
- `remove_kerning_pair` - Remove kerning pair
- `create_kerning_class` - Create kerning class
- `auto_kern` - Auto-generate kerning
- `import_kerning` - Import kerning from file
- `export_kerning` - Export kerning data
- `set_metrics_class` - Create/update metrics class
- `set_glyph_sidebearings` - Set left/right sidebearings
- `auto_metrics` - Auto-calculate metrics

### B. CONTOURS & SHAPES (High Value)

**Resources:**
- `fontlab://glyph/{name}/contours` - Get contour data
- `fontlab://glyph/{name}/paths` - Get path data with nodes

**Tools:**
- `add_contour` - Add contour to glyph from path data
- `remove_contour` - Remove contour by index
- `modify_contour` - Modify nodes in contour
- `reverse_contour` - Reverse contour direction
- `simplify_contour` - Simplify/optimize paths
- `union_shapes` - Boolean union
- `intersect_shapes` - Boolean intersection
- `subtract_shapes` - Boolean subtraction
- `outline_stroke` - Convert stroke to outline
- `add_node` - Add node to contour
- `remove_node` - Remove node from contour
- `convert_node_type` - Change curve/corner type
- `align_nodes` - Align selected nodes
- `distribute_nodes` - Distribute nodes evenly

### C. ANCHORS (Medium Value)

**Resources:**
- `fontlab://glyph/{name}/anchors` - Get anchor positions

**Tools:**
- `add_anchor` - Add anchor to glyph
- `remove_anchor` - Remove anchor
- `move_anchor` - Reposition anchor
- `auto_anchor` - Auto-position anchors
- `generate_mark_feature` - Generate mark/mkmk features

### D. COMPONENTS (High Value)

**Resources:**
- `fontlab://glyph/{name}/components` - Get component info

**Tools:**
- `add_component` - Add component reference
- `remove_component` - Remove component
- `decompose_glyph` - Break components to outlines
- `transform_component` - Transform specific component
- `auto_build_composites` - Build composite glyphs

### E. OPENTYPE FEATURES (High Value)

**Resources:**
- `fontlab://font/features` - Get all feature code
- `fontlab://font/features/{tag}` - Get specific feature
- `fontlab://font/classes` - Get glyph classes

**Tools:**
- `set_feature_code` - Set OpenType feature code
- `compile_features` - Compile and validate features
- `create_glyph_class` - Create glyph class
- `remove_glyph_class` - Remove glyph class
- `generate_feature` - Auto-generate feature (kern, mark, liga, etc.)

### F. VARIABLE FONTS (Medium-High Value)

**Resources:**
- `fontlab://font/axes` - Get variation axes
- `fontlab://font/masters` - Get font masters
- `fontlab://font/instances` - Get defined instances

**Tools:**
- `add_axis` - Add variation axis
- `remove_axis` - Remove axis
- `add_master` - Add font master
- `set_master_location` - Position master in design space
- `generate_instance` - Generate font instance
- `interpolate_glyphs` - Interpolate between masters
- `create_variable_font` - Export variable font

### G. LAYERS (Medium Value)

**Resources:**
- `fontlab://glyph/{name}/layers` - Get layer info

**Tools:**
- `add_layer` - Add layer to glyph
- `remove_layer` - Remove layer
- `copy_layer` - Copy layer contents
- `merge_layers` - Merge layers

### H. GUIDES & ZONES (Low-Medium Value)

**Resources:**
- `fontlab://font/guides` - Get global guides
- `fontlab://font/zones` - Get alignment zones

**Tools:**
- `add_guide` - Add guide
- `remove_guide` - Remove guide
- `add_zone` - Add alignment zone
- `add_stem` - Add stem hint

### I. ADVANCED GLYPH OPERATIONS (Medium Value)

**Resources:**
- `fontlab://glyphs/search` - Search glyphs (by unicode, name pattern, etc.)
- `fontlab://glyph/{name}/metadata` - Get tags, notes, marks

**Tools:**
- `rename_glyph` - Rename glyph
- `duplicate_glyph` - Duplicate glyph
- `copy_glyph_to_font` - Copy between fonts
- `set_glyph_unicode` - Set/change unicode
- `set_glyph_note` - Set note
- `set_glyph_tags` - Set tags
- `set_glyph_mark` - Set color mark
- `find_replace_glyph` - Find and replace by pattern
- `sort_glyphs` - Reorder glyphs

### J. FONT VALIDATION & ANALYSIS (Medium Value)

**Resources:**
- `fontlab://font/validation` - Get validation errors
- `fontlab://font/statistics` - Get font statistics

**Tools:**
- `validate_font` - Run font validation
- `find_overlaps` - Find overlapping paths
- `find_open_paths` - Find open contours
- `find_wrong_directions` - Check path directions
- `auto_fix_contours` - Auto-fix common issues
- `analyze_spacing` - Analyze glyph spacing

### K. IMPORT/EXPORT (Medium Value)

**Tools:**
- `import_font` - Import font file
- `import_glyphs` - Import specific glyphs
- `import_ufo` - Import UFO
- `export_ufo` - Export UFO
- `export_glif` - Export glyphs as GLIF
- `batch_export` - Export multiple formats

### L. COLOR FONTS (Low-Medium Value)

**Resources:**
- `fontlab://glyph/{name}/color-layers` - Get color layers

**Tools:**
- `add_color_layer` - Add color layer
- `set_layer_color` - Set layer color
- `import_svg` - Import SVG to glyph
- `export_svg` - Export glyph as SVG

### M. APPLICATION CONTROL (Medium Value)

**Resources:**
- `fontlab://workspace/preferences` - Get preferences
- `fontlab://workspace/viewport` - Get viewport state

**Tools:**
- `update_viewport` - Refresh view
- `set_preference` - Change preference
- `run_action_set` - Execute action set
- `execute_macro` - Run macro/script
- `open_font` - Open font file
- `close_font` - Close font
- `save_font` - Save current font

### N. BATCH OPERATIONS (High Value for Automation)

**Tools:**
- `batch_transform` - Transform multiple glyphs
- `batch_rename` - Rename glyphs by pattern
- `batch_unicode` - Assign unicodes by pattern
- `batch_create_glyphs` - Create multiple glyphs
- `batch_delete_glyphs` - Delete multiple glyphs
- `apply_to_selection` - Apply operation to selected glyphs

### O. HINTING (Low Value - Specialized)

**Tools:**
- `auto_hint_ps` - Auto-hint PostScript
- `auto_hint_tt` - Auto-hint TrueType
- `clear_hints` - Remove all hints

---

## Implementation Roadmap

### PHASE 1: CORE EXPANSION (Highest Impact)
**Priority: Immediate - Covers most common use cases**

1. **Contours & Shapes** (Category B)
   - Path data access and manipulation
   - Boolean operations
   - Node operations
   - ~15 tools

2. **Kerning & Metrics** (Category A)
   - Kerning pair management
   - Kerning classes
   - Metrics classes
   - ~9 tools

3. **Components** (Category D)
   - Component operations
   - Composite glyph building
   - ~5 tools

4. **Advanced Glyph Operations** (Category I)
   - Glyph search, rename, duplicate
   - Metadata (tags, notes, marks)
   - ~9 tools

**Estimated: ~38 new tools + 8 resources**

---

### PHASE 2: PROFESSIONAL FEATURES (High Value)
**Priority: Next - Enables professional font production**

5. **OpenType Features** (Category E)
   - Feature code management
   - Glyph classes
   - Feature compilation
   - ~6 tools

6. **Variable Fonts** (Category F)
   - Axes and masters
   - Interpolation
   - Instance generation
   - ~7 tools

7. **Font Validation & Analysis** (Category J)
   - Validation
   - Auto-fix tools
   - ~6 tools

8. **Import/Export** (Category K)
   - Enhanced import/export
   - UFO support
   - ~6 tools

**Estimated: ~25 new tools + 10 resources**

---

### PHASE 3: SPECIALIZED FEATURES (Medium Value)
**Priority: Optional - Niche but valuable**

9. **Anchors** (Category C)
   - Anchor management
   - Mark feature generation
   - ~5 tools

10. **Layers** (Category G)
    - Layer operations
    - ~4 tools

11. **Guides & Zones** (Category H)
    - Guide management
    - Alignment zones
    - ~4 tools

12. **Application Control** (Category M)
    - Workspace control
    - Preferences
    - Action sets
    - ~7 tools

**Estimated: ~20 new tools + 6 resources**

---

### PHASE 4: AUTOMATION & SPECIALTY (Lower Priority)
**Priority: Future - Automation and specialized workflows**

13. **Batch Operations** (Category N)
    - Bulk transformations
    - Pattern-based operations
    - ~6 tools

14. **Color Fonts** (Category L)
    - Color layer support
    - SVG import/export
    - ~4 tools

15. **Hinting** (Category O)
    - Auto-hinting
    - ~3 tools

**Estimated: ~13 new tools + 2 resources**

---

## Quick Wins (Recommended Starting Point)

These provide immediate value with moderate effort:

1. **Glyph search/filtering** - Very useful for LLMs
   - `fontlab://glyphs/search?pattern=A*`
   - `fontlab://glyphs/by-unicode/{codepoint}`

2. **Glyph rename/duplicate** - Common operations
   - `rename_glyph(old_name, new_name)`
   - `duplicate_glyph(name, new_name)`

3. **LSB/RSB adjustment** - Basic metrics control
   - `set_sidebearings(name, lsb, rsb)`

4. **Glyph metadata** (tags, notes) - Organization
   - `set_glyph_note(name, note)`
   - `set_glyph_tags(name, tags)`

5. **Basic kerning pairs** - Essential typography
   - `set_kerning_pair(left, right, value)`
   - `fontlab://font/kerning`

---

## Total Scope Estimate

**Features Identified:**
- **~96 new tools** across all phases
- **~26 new resources** for data access
- **Current: 6 tools + 4 resources**
- **Full coverage: 102 tools + 30 resources**

**Development Effort:**
- Phase 1: 3-4 weeks (high impact)
- Phase 2: 2-3 weeks (professional features)
- Phase 3: 2-3 weeks (specialized)
- Phase 4: 1-2 weeks (automation)

**Total: ~8-12 weeks for complete API coverage**

---

## Architecture Recommendations

### Improvements to Consider

1. **Caching Layer** - Cache font info to reduce bridge calls
2. **Batch Mode** - Bundle multiple operations into single script execution
3. **Event Hooks** - Listen for font changes in FontLab
4. **Better Error Handling** - Propagate FontLab errors with context
5. **Streaming Support** - For large data (e.g., all contour paths)
6. **Async Improvements** - Non-blocking operations where possible
7. **Type Validation** - Validate parameters before sending to FontLab
8. **Result Formatting** - Use FontLab 8's HTML output for rich responses

---

## Useful Resources

### Official Documentation
- Main API: https://fontlabcom.github.io/fontlab-python-docs/
- FontLab 8 scripting: https://help.fontlab.com/fontlab/8/whats-new/whats-new-12-scripts-extensions/
- Extend FontLab: https://extend.fontlab.com/

### Key Classes to Study
- `flWorkspace` - Application control
- `flPackage` - Font container
- `flGlyph` - Glyph operations
- `flLayer` - Layer operations
- `fgFont` - Low-level font operations
- `fgKerning` - Kerning management
- `fgContour` - Path/contour operations
- `fgComponent` - Component operations
- `fgAnchor` - Anchor management

---

## Next Actions

1. ✅ Save this research document
2. ⬜ Start with "Quick Wins" implementation
3. ⬜ Test FontLab bridge with actual FontLab installation
4. ⬜ Implement Phase 1 features iteratively
5. ⬜ Add comprehensive error handling
6. ⬜ Create test suite for FontLab integration
7. ⬜ Document each new tool/resource as implemented
