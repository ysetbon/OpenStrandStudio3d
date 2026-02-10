"""
OpenStrandStudio 3D - Layer State Manager
Manages the state of all strands and their connections in the canvas.

CONNECTION STRUCTURE:
====================

The LayerStateManager tracks connections in the format: w: [x(end_point), y(end_point)]
where:
- w = strand name (e.g., '1_1', '1_2', '1_3')
- x = strand connected to w's STARTING point with its end point (0=start, 1=end)
- y = strand connected to w's ENDING point with its end point (0=start, 1=end)
- Format: 'strand_name(end_point)' where end_point is 0 for start, 1 for end

Examples:
--------
1. Simple attachment: 1_2 attached to 1_1's ending point
   - 1_1: ['null', '1_2(0)']  (1_1's start is free, 1_1's end connects to 1_2's start)
   - 1_2: ['1_1(1)', 'null']  (1_2's start connects to 1_1's end, 1_2's end is free)

2. Multiple attachments: 1_2 and 1_3 attached to 1_1's different ends
   - 1_1: ['1_3(0)', '1_2(0)'] (1_1's start connects to 1_3's start, 1_1's end connects to 1_2's start)
   - 1_2: ['1_1(1)', 'null']  (1_2's start connects to 1_1's end, 1_2's end is free)
   - 1_3: ['1_1(0)', 'null']  (1_3's start connects to 1_1's start, 1_3's end is free)

3. Chain of attachments: 1_3 attached to 1_2's ending point
   - 1_1: ['null', '1_2(0)']  (1_1's start is free, 1_1's end connects to 1_2's start)
   - 1_2: ['1_1(1)', '1_3(0)'] (1_2's start connects to 1_1's end, 1_2's end connects to 1_3's start)
   - 1_3: ['1_2(1)', 'null']  (1_3's start connects to 1_2's end, 1_3's end is free)

Connection Types:
----------------
1. Attached Strand Relationships (Parent-Child):
   - Child strand's starting point (0) connects to parent strand's end point
   - The end point of the parent depends on the child's attachment_side:
     * attachment_side = 0: Child connects to parent's start (0)
     * attachment_side = 1: Child connects to parent's end (1)
   - Child strand has a 'parent_strand' attribute pointing to the parent strand
   - Parent strand has the child in its 'attached_strands' list
   - Connections are bidirectional: if A connects to B, then B also shows A
"""

from PyQt5.QtCore import QObject, pyqtSlot


class LayerStateManager(QObject):
    """
    Manages the state of all strands and their connections in the 3D canvas.

    Adapted from the v106 2D LayerStateManager for the 3D OpenStrandStudio.
    Key differences from v106:
    - Uses strand.name instead of strand.layer_name
    - Uses strand.parent_strand instead of strand.parent
    - Positions are 6-tuples (sx, sy, sz, ex, ey, ez) from numpy arrays
    - No MaskedStrand or shadow_overrides (not yet in 3D)
    """

    def __init__(self, canvas=None):
        super().__init__()
        self.canvas = canvas
        self.layer_panel = None
        self.layer_state = {
            'order': [],           # Unique set numbers in order: ['1', '2', ...]
            'connections': {},     # {strand_name: [start_conn, end_conn]}
            'colors': {},          # {strand_name: (r, g, b, a)}
            'positions': {},       # {strand_name: (sx, sy, sz, ex, ey, ez)}
            'selected_strand': None,
            'newest_strand': None,
            'newest_layer': None,
        }

        # Prevent connection recalculation during movement operations
        self.movement_in_progress = False
        self.cached_connections = None

        if canvas:
            self.set_canvas(canvas)

    def set_canvas(self, canvas):
        """Connect to the canvas and its signals."""
        self.canvas = canvas

        # Connect to canvas signals
        if hasattr(canvas, 'strand_created'):
            canvas.strand_created.connect(self.on_strand_created)
        if hasattr(canvas, 'strand_deleted'):
            canvas.strand_deleted.connect(self.on_strand_deleted)

        # Initialize state based on current canvas strands
        self.save_current_state()

    def set_layer_panel(self, layer_panel):
        """Store reference to the layer panel."""
        self.layer_panel = layer_panel

    # ==================== State Management ====================

    def save_current_state(self):
        """Save the current state of all layers by rebuilding from canvas.strands."""
        if not self.canvas:
            return

        try:
            strands = self.canvas.strands

            self.layer_state = {
                'order': list(dict.fromkeys(
                    s.name.split('_')[0] for s in strands if '_' in s.name
                )),
                'connections': self.get_layer_connections(strands),
                'colors': {s.name: s.color for s in strands},
                'positions': {
                    s.name: tuple(s.start.tolist()) + tuple(s.end.tolist())
                    for s in strands
                },
                'selected_strand': (
                    self.canvas.selected_strand.name
                    if self.canvas.selected_strand else None
                ),
                'newest_strand': (
                    strands[-1].name if strands else None
                ),
                'newest_layer': (
                    strands[-1].name.split('_')[0] if strands and '_' in strands[-1].name else None
                ),
            }

            # Populate strand objects' connection fields
            self._update_strand_connection_fields()

        except Exception as e:
            print(f"LayerStateManager: Error saving state: {e}")

    # ==================== Connection Computation ====================

    def get_layer_connections(self, strands):
        """
        Compute bidirectional connections for all strands.

        Returns:
            dict: {strand_name: [start_connection_str, end_connection_str]}

        Format: 'connected_strand_name(end_point)' where end_point is:
          0 = connected at its start point
          1 = connected at its end point
        'null' if no connection at that end.
        """
        from attached_strand import AttachedStrand

        # During movement, return cached connections
        if self.movement_in_progress and self.cached_connections is not None:
            return self.cached_connections

        connections = {}

        for strand in strands:
            start_connection = None
            start_end_point = None
            end_connection = None
            end_end_point = None

            # 1. If this strand is an AttachedStrand, its START connects to parent
            if isinstance(strand, AttachedStrand) and strand.parent_strand:
                start_connection = strand.parent_strand.name
                # attachment_side tells us WHICH end of the parent
                start_end_point = strand.attachment_side  # 0=parent's start, 1=parent's end

            # 2. Check attached children (connected to THIS strand's endpoints)
            for attached in strand.attached_strands:
                if not isinstance(attached, AttachedStrand):
                    continue
                child_side = getattr(attached, 'attachment_side', None)
                if child_side is None:
                    continue

                if child_side == 0:  # Child attached to our START
                    if start_connection is None:  # Only set if not already set
                        start_connection = attached.name
                        start_end_point = 0  # Child's start point
                elif child_side == 1:  # Child attached to our END
                    if end_connection is None:  # Only set if not already set
                        end_connection = attached.name
                        end_end_point = 0  # Child's start point

            # 3. Format connections
            start_fmt = f"{start_connection}({start_end_point})" if start_connection else 'null'
            end_fmt = f"{end_connection}({end_end_point})" if end_connection else 'null'

            connections[strand.name] = [start_fmt, end_fmt]

        return connections

    def _update_strand_connection_fields(self):
        """
        Populate start_connection and end_connection on each Strand object.

        This fills in the existing (but previously unused) fields defined in
        strand.py: start_connection and end_connection.
        Format: {'strand': Strand, 'end': 'start'/'end'} or None
        """
        connections = self.layer_state.get('connections', {})
        strand_lookup = {s.name: s for s in self.canvas.strands}

        for strand in self.canvas.strands:
            conn_data = connections.get(strand.name, ['null', 'null'])

            # Parse start connection
            strand.start_connection = self._parse_connection_ref(
                conn_data[0], strand_lookup
            )
            # Parse end connection
            strand.end_connection = self._parse_connection_ref(
                conn_data[1], strand_lookup
            )

    def _parse_connection_ref(self, conn_str, strand_lookup):
        """
        Parse 'strand_name(end_point)' into {'strand': Strand, 'end': 'start'/'end'}.

        Args:
            conn_str: Connection string like '1_2(0)' or 'null'
            strand_lookup: Dict mapping strand names to Strand objects

        Returns:
            dict with 'strand' and 'end' keys, or None if no connection
        """
        if conn_str == 'null' or not conn_str:
            return None

        # Parse format: "1_2(0)" or "1_2(1)"
        paren_idx = conn_str.rfind('(')
        if paren_idx < 0:
            return None

        name = conn_str[:paren_idx]
        end_point = conn_str[paren_idx + 1:-1]  # "0" or "1"

        target = strand_lookup.get(name)
        if target is None:
            return None

        return {
            'strand': target,
            'end': 'start' if end_point == '0' else 'end'
        }

    # ==================== Movement Caching ====================

    def start_movement_operation(self):
        """
        Start a movement operation - cache connections and prevent recalculation.

        Called at the beginning of a drag operation to freeze the connection state.
        This avoids expensive recomputation on every frame during drag.
        """
        self.movement_in_progress = True
        # Cache the current connections to prevent recalculation during movement
        if self.canvas and hasattr(self.canvas, 'strands'):
            self.cached_connections = self.get_layer_connections(self.canvas.strands)

    def end_movement_operation(self):
        """
        End a movement operation - allow connection recalculation.

        Called at the end of a drag operation to unfreeze and recompute state.
        """
        self.movement_in_progress = False
        self.cached_connections = None
        # Force a state save to update positions
        self.save_current_state()

    # ==================== Signal Handlers ====================

    @pyqtSlot(str)
    def on_strand_created(self, strand_name):
        """Called when a new strand is created or attached."""
        self.save_current_state()

    @pyqtSlot(str)
    def on_strand_deleted(self, strand_name):
        """Called when a strand is deleted."""
        if not self.movement_in_progress:
            # Clean up references to deleted strand in connections
            connections = self.layer_state.get('connections', {})
            if strand_name in connections:
                del connections[strand_name]

            # Update references to this strand in other strands' connections
            for other_name, conn_data in connections.items():
                if isinstance(conn_data, list) and len(conn_data) == 2:
                    if conn_data[0] and strand_name in str(conn_data[0]):
                        conn_data[0] = 'null'
                    if conn_data[1] and strand_name in str(conn_data[1]):
                        conn_data[1] = 'null'

        # Recalculate full state
        self.save_current_state()

    # ==================== Getters (v106 API compatibility) ====================

    def getConnections(self):
        """Return the current layer connections."""
        # During movement operations, use cached connections
        if self.movement_in_progress and self.cached_connections is not None:
            return self.cached_connections
        return self.layer_state.get('connections', {})

    def getDetailedConnections(self):
        """Return the detailed layer connections with start/end information."""
        connections = self.layer_state.get('connections', {})

        detailed = {}
        for strand_name, conn_data in connections.items():
            if isinstance(conn_data, list) and len(conn_data) == 2:
                start_conn = conn_data[0] if conn_data[0] != 'null' else None
                end_conn = conn_data[1] if conn_data[1] != 'null' else None
                detailed[strand_name] = {
                    'start': start_conn,
                    'end': end_conn,
                }
            else:
                detailed[strand_name] = {
                    'start': None,
                    'end': None,
                }

        return detailed

    def getOrder(self):
        """Get the current order of set numbers."""
        return self.layer_state.get('order', [])

    def getColors(self):
        """Get the current colors of all strands."""
        return self.layer_state.get('colors', {})

    def getPositions(self):
        """Get the current positions of all strands."""
        return self.layer_state.get('positions', {})

    def getSelectedStrand(self):
        """Get the currently selected strand name."""
        return self.layer_state.get('selected_strand')

    def getNewestStrand(self):
        """Get the newest strand name."""
        return self.layer_state.get('newest_strand')

    def getNewestLayer(self):
        """Get the newest layer (set number)."""
        return self.layer_state.get('newest_layer')

    # ==================== Connection Management ====================

    def removeStrandConnections(self, strand_name):
        """
        Remove all connections for a deleted strand.

        Args:
            strand_name: Name of the strand to remove connections for
        """
        # Don't remove connections during movement operations
        if self.movement_in_progress:
            return

        connections = self.layer_state.get('connections', {})

        # Remove the strand from connections dict
        if strand_name in connections:
            del connections[strand_name]

        # Update references to this strand in other strands' connections
        for other_name, conn_data in connections.items():
            if isinstance(conn_data, list) and len(conn_data) == 2:
                if conn_data[0] and strand_name in str(conn_data[0]):
                    conn_data[0] = 'null'
                if conn_data[1] and strand_name in str(conn_data[1]):
                    conn_data[1] = 'null'

        # Save the updated state
        self.save_current_state()
