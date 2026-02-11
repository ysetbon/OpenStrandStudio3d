"""
OpenStrandStudio 3D - Strand Class
3D Bezier curve strand with control points
"""

import numpy as np
from OpenGL.GL import *
from OpenGL.GLU import *


class Strand:
    """
    A 3D strand represented as a cubic Bezier curve.

    Control points:
    - start: Starting point of the strand
    - end: Ending point of the strand
    - control_point1: First Bezier control point (influences curve near start)
    - control_point2: Second Bezier control point (influences curve near end)
    """

    # Class-level flag to defer VBO cleanup during drag operations (performance optimization)
    _defer_vbo_cleanup = False

    def __init__(self, start, end, name="", color=None, width=0.15):
        """
        Initialize a 3D strand.

        Args:
            start: numpy array [x, y, z] - start position
            end: numpy array [x, y, z] - end position
            name: strand identifier (e.g., "1_1", "1_2")
            color: RGB tuple (0-1 range), default is light blue (#aaaaff)
            width: tube radius for rendering
        """
        self.name = name
        self.start = np.array(start, dtype=float)
        self.end = np.array(end, dtype=float)

        # Visual properties
        self.color = color if color else (0.667, 0.667, 1.0, 1.0)  # Light blue #aaaaff default with full opacity
        self.width = width
        self.height_ratio = 0.4  # Height is 40% of width (2.5:1 flat ratio for plastic leather look)
        self.cross_section_shape = 'ellipse'  # Shape type: 'ellipse', 'rectangle', 'circle', 'diamond', 'hexagon'
        self.corner_radius = 0.0  # Corner radius for rectangle (0-1, as fraction of min dimension)
        self.visible = True

        # Geometry caches (invalidated on control point changes)
        self._geom_version = 0
        self._curve_cache = {}
        self._frame_cache = {}
        self._chain_cache = {}
        self._vbo_cache = {}
        self._vbo_enabled = True

        # Calculate initial control points (1/3 and 2/3 along the strand)
        self._init_control_points()

        # Rendering settings
        self.tube_segments = 40  # Segments around circumference (balanced for speed/quality)
        self.curve_segments = 56  # Segments along curve length for smoother bends

        # Twist angles (in degrees) - controls rotation of the flat cross-section
        # These allow the strand surface to rotate/twist along its length
        self.start_twist = 0.0      # Twist angle at start point
        self.end_twist = 0.0        # Twist angle at end point
        self.cp1_twist = 0.0        # Twist angle at control point 1
        self.cp2_twist = 0.0        # Twist angle at control point 2

        # Selection/highlight state
        self.is_selected = False
        self.is_hovered = False

        # Attached strands (children)
        self.attached_strands = []

        # Track which ends have attached children (mirrors 2D has_circles concept)
        # [0] = start end occupied, [1] = end end occupied
        self.has_circles = [False, False]

        # Connection info (for LayerStateManager compatibility)
        self.start_connection = None  # {'strand': Strand, 'end': 'start'/'end'}
        self.end_connection = None

    def _init_control_points(self):
        """Initialize control points based on start and end positions"""
        direction = self.end - self.start

        # Place control points at 1/3 and 2/3 along the strand
        # Keep them in the same XZ plane as start/end (no Y offset)
        self.control_point1 = self.start + direction * 0.33
        self.control_point2 = self.start + direction * 0.67
        self._mark_geometry_dirty()

    def _mark_geometry_dirty(self):
        """Invalidate cached curve data when geometry changes."""
        self._geom_version += 1
        self._curve_cache.clear()
        self._frame_cache.clear()
        if len(self._chain_cache) > 0:
            self._chain_cache.clear()
        # Skip VBO deletion during drag - deferred to drag end for performance
        if not Strand._defer_vbo_cleanup:
            self._clear_vbo_cache()

    def _clear_vbo_cache(self):
        """Delete cached VBOs to avoid stale geometry and GPU leaks."""
        if not self._vbo_cache:
            return
        for entry in self._vbo_cache.values():
            self._delete_vbo_entry(entry)
        self._vbo_cache.clear()

    def _delete_vbo_entry(self, entry):
        """Delete VBO resources safely."""
        if not entry:
            return
        buffers = [entry.get("vbo_vertices"), entry.get("vbo_normals")]
        buffers = [buf for buf in buffers if buf]
        if not buffers:
            return
        try:
            glDeleteBuffers(buffers)
        except Exception:
            pass

    def _prune_vbo_cache(self, max_entries=6):
        """Limit VBO cache growth by clearing when it gets too large."""
        if len(self._vbo_cache) <= max_entries:
            return
        # During drag, allow larger cache to avoid GPU sync
        if Strand._defer_vbo_cleanup:
            if len(self._vbo_cache) <= max_entries * 5:  # Allow 30 entries during drag
                return
        self._clear_vbo_cache()

    @classmethod
    def begin_drag_operation(cls):
        """Call at start of drag to defer VBO cleanup for performance."""
        cls._defer_vbo_cleanup = True

    @classmethod
    def end_drag_operation(cls, strands=None):
        """Call at end of drag to flush deferred VBO cleanup.

        Args:
            strands: Optional list of strands to clear VBOs for. If None, does nothing
                     (VBOs will be rebuilt on next render automatically).
        """
        cls._defer_vbo_cleanup = False
        # VBOs are stale but will be rebuilt on next render - no need to explicitly clear

    def update_has_circles(self):
        """Recompute has_circles from attached_strands list."""
        self.has_circles[0] = any(
            getattr(child, 'attachment_side', None) == 0
            for child in self.attached_strands
        )
        self.has_circles[1] = any(
            getattr(child, 'attachment_side', None) == 1
            for child in self.attached_strands
        )

    def is_deletable(self):
        """A strand is deletable if not both ends are occupied by children."""
        return not all(self.has_circles)

    def get_bezier_point(self, t):
        """
        Get a point on the cubic Bezier curve at parameter t.

        Args:
            t: Parameter from 0 to 1

        Returns:
            numpy array [x, y, z]
        """
        # Cubic Bezier formula: B(t) = (1-t)³P0 + 3(1-t)²tP1 + 3(1-t)t²P2 + t³P3
        t2 = t * t
        t3 = t2 * t
        mt = 1 - t
        mt2 = mt * mt
        mt3 = mt2 * mt

        return (mt3 * self.start +
                3 * mt2 * t * self.control_point1 +
                3 * mt * t2 * self.control_point2 +
                t3 * self.end)

    def get_bezier_tangent(self, t):
        """
        Get the tangent vector at parameter t on the Bezier curve.

        Args:
            t: Parameter from 0 to 1

        Returns:
            numpy array [x, y, z] (normalized)
        """
        # Derivative of cubic Bezier
        t2 = t * t
        mt = 1 - t
        mt2 = mt * mt

        tangent = (3 * mt2 * (self.control_point1 - self.start) +
                   6 * mt * t * (self.control_point2 - self.control_point1) +
                   3 * t2 * (self.end - self.control_point2))

        # Normalize
        length = np.linalg.norm(tangent)
        if length > 1e-6:
            tangent /= length

        return tangent

    def get_curve_points(self, num_segments=None):
        """
        Get array of points along the Bezier curve (vectorized).

        Args:
            num_segments: Number of segments (default: self.curve_segments)

        Returns:
            List of numpy arrays
        """
        if num_segments is None:
            num_segments = self.curve_segments

        cached = self._curve_cache.get(num_segments)
        if cached and cached[0] == self._geom_version:
            return cached[1]

        # Vectorized Bezier: compute all points in one numpy operation
        t = np.linspace(0.0, 1.0, num_segments + 1, dtype=np.float64)  # (S+1,)
        t2 = t * t
        t3 = t2 * t
        mt = 1.0 - t
        mt2 = mt * mt
        mt3 = mt2 * mt
        # Broadcast (S+1,1) * (3,) → (S+1, 3)
        pts = (mt3[:, None] * self.start[None, :] +
               (3.0 * mt2 * t)[:, None] * self.control_point1[None, :] +
               (3.0 * mt * t2)[:, None] * self.control_point2[None, :] +
               t3[:, None] * self.end[None, :])
        points = [pts[i] for i in range(len(pts))]

        self._curve_cache[num_segments] = (self._geom_version, points)
        return points

    def _get_curve_points_and_frames(self, num_segments=None):
        """Return cached curve points and frames for the given resolution."""
        if num_segments is None:
            num_segments = self.curve_segments

        points = self.get_curve_points(num_segments)
        if len(points) < 2:
            return points, []

        cached = self._frame_cache.get(num_segments)
        if cached and cached[0] == self._geom_version:
            return points, cached[1]

        # Compute parallel transport frames
        frames = self._compute_parallel_frames(points)

        # Apply twist rotation to frames based on twist angles
        frames = self._apply_twist_to_frames(frames, points)

        self._frame_cache[num_segments] = (self._geom_version, frames)
        return points, frames

    def draw(self, is_selected=False, is_hovered=False, lod=None):
        """
        Draw the strand as a 3D tube along the Bezier curve.

        Args:
            is_selected: Whether this strand is selected
            is_hovered: Whether mouse is hovering over this strand
        """
        if not self.visible:
            return

        self.is_selected = is_selected
        self.is_hovered = is_hovered

        # Use strand's actual color with alpha (selection highlight is drawn separately)
        color = self.color
        if len(color) >= 4:
            glColor4f(color[0], color[1], color[2], color[3])
        else:
            glColor4f(color[0], color[1], color[2], 1.0)

        curve_segments = self.curve_segments
        tube_segments = self.tube_segments
        cap_segments = 32
        if lod:
            curve_segments = lod.get("curve_segments", curve_segments)
            tube_segments = lod.get("tube_segments", tube_segments)
            cap_segments = lod.get("cap_segments", cap_segments)

        # Chain roots draw the entire chain as one continuous spline.
        # Non-roots are drawn as part of their parent's chain.
        if self._is_chain_root():
            self._draw_chain_as_spline(
                curve_segments=curve_segments,
                tube_segments=tube_segments,
                cap_segments=cap_segments
            )

    def draw_selection_highlight(self, lod=None):
        """
        Draw a semi-transparent highlight overlay for this strand only.
        Used to show which strand is selected within a chain.
        """
        self._draw_highlight(color=(1.0, 0.0, 0.0, 0.2), width_scale=1.5, lod=lod)

    def draw_hover_highlight(self, lod=None):
        """Draw a subtle hover highlight for this strand."""
        self._draw_highlight(color=(1.0, 0.85, 0.2, 0.25), width_scale=1.25, lod=lod)

    def draw_edit_all_highlight(self, lod=None):
        """
        Draw a red highlight for strand being moved/hovered in Edit All mode.
        Similar to selection highlight but for temporarily active strands.
        """
        self._draw_highlight(color=(1.0, 0.2, 0.2, 0.3), width_scale=1.4, lod=lod)

    def _draw_highlight(self, color, width_scale, lod=None):
        """Draw a semi-transparent overlay along this strand."""
        if not self.visible:
            return

        curve_segments = self.curve_segments
        tube_segments = self.tube_segments
        if lod:
            curve_segments = lod.get("curve_segments", curve_segments)
            tube_segments = lod.get("tube_segments", tube_segments)

        curve_points, frames = self._get_curve_points_and_frames(curve_segments)
        if len(frames) < 2:
            return

        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glDepthMask(GL_FALSE)
        glColor4f(*color)

        # Temporarily scale width to build highlight mesh
        orig_width = self.width
        self.width = orig_width * width_scale
        vertices, normals = self._build_tube_mesh(curve_points, frames, tube_segments)
        self.width = orig_width

        if vertices.size > 0:
            glEnableClientState(GL_VERTEX_ARRAY)
            glEnableClientState(GL_NORMAL_ARRAY)
            glVertexPointer(3, GL_FLOAT, 0, vertices)
            glNormalPointer(GL_FLOAT, 0, normals)
            glDrawArrays(GL_TRIANGLES, 0, vertices.size // 3)
            glDisableClientState(GL_NORMAL_ARRAY)
            glDisableClientState(GL_VERTEX_ARRAY)

        glDepthMask(GL_TRUE)
        glDisable(GL_BLEND)

    def _is_chain_root(self):
        """Check if this strand is the root of a chain (not attached to another strand)"""
        # Base Strand class is always a root
        # AttachedStrand will override this to return False
        return True

    def _get_chain_strands(self):
        """
        Get all strands in this chain, in order from root to leaves.
        Returns a list of strand chains (each chain is a list of strands).
        For now, we follow the first attached strand at each level (linear chain).
        """
        chains = []
        self._collect_chains([], chains)
        return chains

    def _collect_chains(self, current_chain, all_chains):
        """Recursively collect strand chains"""
        current_chain = current_chain + [self]

        # Find strands attached to our end (attachment_side == 1)
        end_attachments = [s for s in self.attached_strands
                          if hasattr(s, 'attachment_side') and s.attachment_side == 1]

        if not end_attachments:
            # End of chain - save it
            all_chains.append(current_chain)
        else:
            # Continue chain with each attached strand
            for attached in end_attachments:
                attached._collect_chains(current_chain, all_chains)

    def _draw_single_strand(self, curve_segments=None, tube_segments=None, cap_segments=32):
        """Draw just this single strand (used during drag for performance).

        During drag, we use immediate mode (no VBOs) to avoid the overhead of
        creating new VBOs every frame as geometry changes.
        """
        if curve_segments is None:
            curve_segments = self.curve_segments
        if tube_segments is None:
            tube_segments = self.tube_segments

        # Get curve points and frames for just this strand
        curve_points, frames = self._get_curve_points_and_frames(curve_segments)
        if len(curve_points) < 2:
            return

        # During drag: use immediate mode (no VBO creation overhead)
        self._draw_tube_from_points(curve_points, frames, tube_segments=tube_segments)

        # Draw end caps ONLY at true ends (not at connection points)
        # This prevents visual gaps when rendering strands individually

        # Check if START is connected (this is an AttachedStrand with a parent)
        start_connected = hasattr(self, 'parent_strand') and self.parent_strand is not None

        # Check if END is connected (has attached strands at end, i.e., attachment_side == 1)
        end_connected = False
        if hasattr(self, 'attached_strands'):
            for attached in self.attached_strands:
                if hasattr(attached, 'attachment_side') and attached.attachment_side == 1:
                    end_connected = True
                    break

        # Only draw caps at unconnected ends
        if not start_connected:
            tangent_start = self.get_bezier_tangent(0.0)
            self._draw_shape_cap(self.start, -tangent_start, segments=cap_segments)

        if not end_connected:
            tangent_end = self.get_bezier_tangent(1.0)
            self._draw_shape_cap(self.end, tangent_end, segments=cap_segments)

    def _draw_chain_as_spline(self, curve_segments=None, tube_segments=None, cap_segments=32):
        """Draw the entire strand chain as one continuous Bezier spline."""
        if curve_segments is None:
            curve_segments = self.curve_segments
        if tube_segments is None:
            tube_segments = self.tube_segments

        chains = self._get_chain_strands()

        for chain in chains:
            if not chain:
                continue

            all_points, frames = self._get_chain_geometry(chain, curve_segments)

            if len(all_points) < 2:
                continue

            if Strand._defer_vbo_cleanup:
                # During drag: try VBO cache for non-affected chains (read-only lookup)
                # If cache hit → render from GPU VBO (fast, chain hasn't changed)
                # If cache miss → use fresh arrays (affected chain, geometry changed)
                versions = tuple((id(s), s._geom_version) for s in chain)
                vbo_key = (curve_segments, tube_segments, versions)
                cached_vbo = self._vbo_cache.get(vbo_key)
                if cached_vbo:
                    self._draw_tube_vbo(cached_vbo)
                else:
                    self._draw_tube_from_points(all_points, frames, tube_segments=tube_segments)
            else:
                # Normal: use VBO cache for fast repeated rendering
                vbo_entry = self._get_or_build_chain_vbo(
                    chain, all_points, frames,
                    curve_segments=curve_segments,
                    tube_segments=tube_segments
                )
                if vbo_entry:
                    self._draw_tube_vbo(vbo_entry)
                else:
                    self._draw_tube_from_points(all_points, frames, tube_segments=tube_segments)

            self._draw_chain_end_caps(chain, all_points, frames, cap_segments=cap_segments)

    def _get_chain_geometry(self, chain, curve_segments):
        """Get cached chain points/frames keyed by strand versions and resolution."""
        versions = tuple((id(strand), strand._geom_version) for strand in chain)
        key = (curve_segments, versions)
        cached = self._chain_cache.get(key)
        if cached:
            return cached

        all_points = []
        for i, strand in enumerate(chain):
            points = strand.get_curve_points(curve_segments)
            if i == 0:
                all_points.extend(points)
            else:
                all_points.extend(points[1:])

        frames = self._compute_chain_frames(all_points)

        # Apply twist to the chain frames based on each strand's twist values
        frames = self._apply_chain_twist(chain, all_points, frames, curve_segments)

        self._chain_cache[key] = (all_points, frames)

        if len(self._chain_cache) > 8:
            self._chain_cache.clear()

        return all_points, frames

    def _apply_chain_twist(self, chain, all_points, frames, curve_segments):
        """
        Apply twist to chain frames based on each strand's twist values.

        For chains with multiple strands, each strand section gets its own
        twist interpolation applied.

        Args:
            chain: List of strands in the chain
            all_points: All curve points for the chain
            frames: Parallel transport frames for all points
            curve_segments: Number of segments per strand

        Returns:
            New list of (right, up) tuples with twist applied
        """
        if len(frames) < 2 or not chain:
            return frames

        twisted_frames = []
        point_index = 0

        for strand_idx, strand in enumerate(chain):
            # Calculate how many points this strand contributes
            if strand_idx == 0:
                strand_point_count = curve_segments + 1
            else:
                strand_point_count = curve_segments  # First point shared with previous

            # Apply twist to each point in this strand's section
            for i in range(strand_point_count):
                if point_index >= len(frames):
                    break

                # Calculate t parameter for this point within the strand (0 to 1)
                t = i / curve_segments if curve_segments > 0 else 0.0

                # Get twist angle at this point using strand's twist values
                twist_deg = strand.get_twist_at_t(t)

                if abs(twist_deg) < 0.01:
                    # No significant twist, keep original frame
                    twisted_frames.append(frames[point_index])
                else:
                    # Apply twist rotation around tangent
                    right, up = frames[point_index]

                    # Calculate tangent at this point
                    if point_index < len(all_points) - 1:
                        tangent = all_points[point_index + 1] - all_points[point_index]
                    else:
                        tangent = all_points[point_index] - all_points[point_index - 1]
                    tangent_len = np.linalg.norm(tangent)
                    if tangent_len > 1e-6:
                        tangent = tangent / tangent_len
                    else:
                        tangent = np.array([1.0, 0.0, 0.0])

                    # Rotate right and up vectors around tangent
                    twist_rad = np.radians(twist_deg)
                    new_right = self._rotate_vector(right, tangent, twist_rad)
                    new_up = self._rotate_vector(up, tangent, twist_rad)

                    twisted_frames.append((new_right, new_up))

                point_index += 1

        # Handle any remaining frames (shouldn't happen, but be safe)
        while point_index < len(frames):
            twisted_frames.append(frames[point_index])
            point_index += 1

        return twisted_frames

    def _get_or_build_chain_vbo(self, chain, points, frames, curve_segments, tube_segments):
        """Get or build a VBO for the given chain geometry and LOD."""
        if not self._vbo_enabled:
            return None

        versions = tuple((id(strand), strand._geom_version) for strand in chain)
        key = (curve_segments, tube_segments, versions)
        cached = self._vbo_cache.get(key)
        if cached:
            return cached

        vertices, normals = self._build_tube_mesh(points, frames, tube_segments)
        if vertices.size == 0:
            return None

        try:
            vbo_vertices = glGenBuffers(1)
            vbo_normals = glGenBuffers(1)
            glBindBuffer(GL_ARRAY_BUFFER, vbo_vertices)
            glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)
            glBindBuffer(GL_ARRAY_BUFFER, vbo_normals)
            glBufferData(GL_ARRAY_BUFFER, normals.nbytes, normals, GL_STATIC_DRAW)
            glBindBuffer(GL_ARRAY_BUFFER, 0)
        except Exception:
            self._vbo_enabled = False
            return None

        entry = {
            "vbo_vertices": vbo_vertices,
            "vbo_normals": vbo_normals,
            "vertex_count": vertices.size // 3
        }
        self._vbo_cache[key] = entry
        self._prune_vbo_cache()
        return entry

    def _build_tube_mesh(self, points, frames, tube_segments):
        """Build triangle mesh data for a tube using vectorized numpy operations.

        Returns flat float32 arrays of (vertices, normals) suitable for
        glVertexPointer / glDrawArrays(GL_TRIANGLES, ...).
        Uses float32 throughout to halve memory and avoid dtype conversion.
        """
        if len(points) < 2 or len(frames) < 2 or tube_segments < 3:
            return np.array([], dtype=np.float32), np.array([], dtype=np.float32)

        cs_points, height_ratio = self._get_cross_section_points(tube_segments)
        ring_count = len(cs_points)
        height = np.float32(self.width * height_ratio)
        width = np.float32(self.width)

        # Convert inputs to float32 arrays throughout
        pts = np.ascontiguousarray(points, dtype=np.float32)
        cs = np.array(cs_points, dtype=np.float32)               # (R, 2)
        N = len(pts) - 1  # number of segments along the curve

        # Unpack frames into (N+1, 3) arrays
        rights = np.array([f[0] for f in frames], dtype=np.float32)  # (N+1, 3)
        ups    = np.array([f[1] for f in frames], dtype=np.float32)  # (N+1, 3)

        # Cross-section factors
        x_cs = cs[:, 0]  # (R,)
        y_cs = cs[:, 1]  # (R,)

        # Next cross-section index (wraps around)
        j_next = np.arange(1, ring_count + 1) % ring_count

        x0 = x_cs                # (R,)
        y0 = y_cs
        x1 = x_cs[j_next]       # (R,)
        y1 = y_cs[j_next]

        # Slice into "current" and "next" along curve
        c1 = pts[:-1]            # (N, 3)
        c2 = pts[1:]             # (N, 3)
        r1 = rights[:-1]         # (N, 3)
        r2 = rights[1:]          # (N, 3)
        u1 = ups[:-1]            # (N, 3)
        u2 = ups[1:]             # (N, 3)

        # Broadcast to (N, R, 3): vertex = center + width*x*right + height*y*up
        v00 = c1[:, None, :] + width * x0[None, :, None] * r1[:, None, :] + height * y0[None, :, None] * u1[:, None, :]
        v01 = c1[:, None, :] + width * x1[None, :, None] * r1[:, None, :] + height * y1[None, :, None] * u1[:, None, :]
        v10 = c2[:, None, :] + width * x0[None, :, None] * r2[:, None, :] + height * y0[None, :, None] * u2[:, None, :]
        v11 = c2[:, None, :] + width * x1[None, :, None] * r2[:, None, :] + height * y1[None, :, None] * u2[:, None, :]

        # Normals (unnormalized): n = x*right + y*up
        n00 = x0[None, :, None] * r1[:, None, :] + y0[None, :, None] * u1[:, None, :]
        n01 = x1[None, :, None] * r1[:, None, :] + y1[None, :, None] * u1[:, None, :]
        n10 = x0[None, :, None] * r2[:, None, :] + y0[None, :, None] * u2[:, None, :]
        n11 = x1[None, :, None] * r2[:, None, :] + y1[None, :, None] * u2[:, None, :]

        # Vectorized normal normalization (all 4 at once instead of loop)
        all_n = np.stack([n00, n01, n10, n11])  # (4, N, R, 3)
        lens = np.linalg.norm(all_n, axis=3, keepdims=True)
        lens[lens < 1e-6] = 1.0
        all_n /= lens
        n00, n01, n10, n11 = all_n[0], all_n[1], all_n[2], all_n[3]

        # Assemble triangles: 2 triangles per quad = 6 vertices per (i, j)
        tris = np.empty((N, ring_count, 6, 3), dtype=np.float32)
        tris[:, :, 0, :] = v00
        tris[:, :, 1, :] = v10
        tris[:, :, 2, :] = v11
        tris[:, :, 3, :] = v00
        tris[:, :, 4, :] = v11
        tris[:, :, 5, :] = v01

        nrms = np.empty((N, ring_count, 6, 3), dtype=np.float32)
        nrms[:, :, 0, :] = n00
        nrms[:, :, 1, :] = n10
        nrms[:, :, 2, :] = n11
        nrms[:, :, 3, :] = n00
        nrms[:, :, 4, :] = n11
        nrms[:, :, 5, :] = n01

        vertices = np.ascontiguousarray(tris.reshape(-1))
        normals  = np.ascontiguousarray(nrms.reshape(-1))

        return vertices, normals

    def _draw_tube_vbo(self, entry):
        """Draw a cached tube mesh from VBOs."""
        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_NORMAL_ARRAY)

        glBindBuffer(GL_ARRAY_BUFFER, entry["vbo_vertices"])
        glVertexPointer(3, GL_FLOAT, 0, None)
        glBindBuffer(GL_ARRAY_BUFFER, entry["vbo_normals"])
        glNormalPointer(GL_FLOAT, 0, None)

        glDrawArrays(GL_TRIANGLES, 0, entry["vertex_count"])

        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glDisableClientState(GL_NORMAL_ARRAY)
        glDisableClientState(GL_VERTEX_ARRAY)

    def _compute_chain_frames(self, points):
        """Compute parallel transport frames for a chain of points (optimized).

        Uses batch tangent computation and pure Python scalar math in the
        sequential loop to avoid numpy function-call overhead (~10-50us each).
        """
        from math import sqrt, acos, cos, sin

        n = len(points)
        if n < 2:
            return []

        # Batch-compute all tangents at once (vectorized)
        pts = np.array(points, dtype=np.float64)  # (N, 3)
        tangents = np.empty((n, 3), dtype=np.float64)
        tangents[:-1] = pts[1:] - pts[:-1]
        tangents[-1] = tangents[-2].copy()
        t_lens = np.linalg.norm(tangents, axis=1, keepdims=True)
        t_lens[t_lens < 1e-6] = 1.0
        tangents /= t_lens

        # Extract to Python lists for zero-overhead loop access
        tan_x = tangents[:, 0].tolist()
        tan_y = tangents[:, 1].tolist()
        tan_z = tangents[:, 2].tolist()

        # Initial frame
        t0x, t0y, t0z = tan_x[0], tan_y[0], tan_z[0]
        if abs(t0y) < 0.9:
            # cross(tangent, [0,1,0])
            rx, ry, rz = t0z, 0.0, -t0x
        else:
            # cross(tangent, [0,0,1])
            rx, ry, rz = -t0y, t0x, 0.0
        r_len = sqrt(rx * rx + ry * ry + rz * rz)
        if r_len > 1e-6:
            rx /= r_len; ry /= r_len; rz /= r_len

        # up = cross(right, tangent)
        ux = ry * t0z - rz * t0y
        uy = rz * t0x - rx * t0z
        uz = rx * t0y - ry * t0x
        u_len = sqrt(ux * ux + uy * uy + uz * uz)
        if u_len > 1e-6:
            ux /= u_len; uy /= u_len; uz /= u_len

        # Pre-allocate output arrays
        rights = np.empty((n, 3), dtype=np.float64)
        ups = np.empty((n, 3), dtype=np.float64)
        rights[0, 0] = rx; rights[0, 1] = ry; rights[0, 2] = rz
        ups[0, 0] = ux; ups[0, 1] = uy; ups[0, 2] = uz

        # Sequential parallel transport with pure Python scalar math
        px, py, pz = t0x, t0y, t0z
        for i in range(1, n):
            tx = tan_x[i]; ty = tan_y[i]; tz = tan_z[i]

            dot = px * tx + py * ty + pz * tz

            if dot < -0.99:
                rx, ry, rz = -rx, -ry, -rz
            elif dot < 0.99:
                # Rotation axis = cross(prev_tangent, tangent)
                ax = py * tz - pz * ty
                ay = pz * tx - px * tz
                az = px * ty - py * tx
                a_len = sqrt(ax * ax + ay * ay + az * az)
                if a_len > 1e-6:
                    ax /= a_len; ay /= a_len; az /= a_len
                    angle = acos(max(-1.0, min(1.0, dot)))
                    cos_a = cos(angle)
                    sin_a = sin(angle)
                    # Rodrigues' rotation of right vector
                    d = ax * rx + ay * ry + az * rz
                    cx = ay * rz - az * ry
                    cy = az * rx - ax * rz
                    cz = ax * ry - ay * rx
                    one_minus_cos = 1.0 - cos_a
                    rx = rx * cos_a + cx * sin_a + ax * d * one_minus_cos
                    ry = ry * cos_a + cy * sin_a + ay * d * one_minus_cos
                    rz = rz * cos_a + cz * sin_a + az * d * one_minus_cos

            # up = cross(right, tangent)
            ux = ry * tz - rz * ty
            uy = rz * tx - rx * tz
            uz = rx * ty - ry * tx
            u_len = sqrt(ux * ux + uy * uy + uz * uz)
            if u_len > 1e-6:
                ux /= u_len; uy /= u_len; uz /= u_len

            # right = cross(tangent, up)
            rx = ty * uz - tz * uy
            ry = tz * ux - tx * uz
            rz = tx * uy - ty * ux
            r_len = sqrt(rx * rx + ry * ry + rz * rz)
            if r_len > 1e-6:
                rx /= r_len; ry /= r_len; rz /= r_len

            rights[i, 0] = rx; rights[i, 1] = ry; rights[i, 2] = rz
            ups[i, 0] = ux; ups[i, 1] = uy; ups[i, 2] = uz
            px = tx; py = ty; pz = tz

        return [(rights[i], ups[i]) for i in range(n)]

    def _rotate_vector(self, v, axis, angle):
        """Rotate vector v around axis by angle (Rodrigues' formula)"""
        cos_a = np.cos(angle)
        sin_a = np.sin(angle)
        return v * cos_a + np.cross(axis, v) * sin_a + axis * np.dot(axis, v) * (1 - cos_a)

    def get_twist_at_t(self, t):
        """
        Get the interpolated twist angle at parameter t along the curve.
        Uses cubic Bezier-style interpolation between the four twist values:
        - t=0: start_twist
        - Control points influence the interpolation curve
        - t=1: end_twist

        Args:
            t: Parameter from 0 to 1

        Returns:
            Twist angle in degrees
        """
        # Use cubic Bezier interpolation for smooth twist transitions
        # The control point twists act like Bezier control weights
        t2 = t * t
        t3 = t2 * t
        mt = 1 - t
        mt2 = mt * mt
        mt3 = mt2 * mt

        return (mt3 * self.start_twist +
                3 * mt2 * t * self.cp1_twist +
                3 * mt * t2 * self.cp2_twist +
                t3 * self.end_twist)

    def _apply_twist_to_frames(self, frames, points):
        """
        Apply twist rotation to computed frames based on twist angles.

        Args:
            frames: List of (right, up) frame tuples from parallel transport
            points: Curve points corresponding to each frame

        Returns:
            New list of (right, up) tuples with twist applied
        """
        if len(frames) < 2:
            return frames

        twisted_frames = []
        n = len(frames)

        for i in range(n):
            # Calculate t parameter for this point
            t = i / (n - 1) if n > 1 else 0.0

            # Get twist angle at this point
            twist_deg = self.get_twist_at_t(t)

            if abs(twist_deg) < 0.01:
                # No significant twist, keep original frame
                twisted_frames.append(frames[i])
            else:
                # Apply twist rotation around tangent
                right, up = frames[i]

                # Calculate tangent at this point
                if i < n - 1:
                    tangent = points[i + 1] - points[i]
                else:
                    tangent = points[i] - points[i - 1]
                tangent_len = np.linalg.norm(tangent)
                if tangent_len > 1e-6:
                    tangent = tangent / tangent_len
                else:
                    tangent = np.array([1.0, 0.0, 0.0])

                # Rotate right and up vectors around tangent
                twist_rad = np.radians(twist_deg)
                new_right = self._rotate_vector(right, tangent, twist_rad)
                new_up = self._rotate_vector(up, tangent, twist_rad)

                twisted_frames.append((new_right, new_up))

        return twisted_frames

    def _draw_tube_from_points(self, points, frames, tube_segments=None):
        """Draw a tube using vectorized mesh + glDrawArrays (no per-vertex GL calls)."""
        if len(points) < 2 or len(frames) < 2:
            return

        if tube_segments is None:
            tube_segments = self.tube_segments

        vertices, normals = self._build_tube_mesh(points, frames, tube_segments)
        if vertices.size == 0:
            return

        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_NORMAL_ARRAY)
        glVertexPointer(3, GL_FLOAT, 0, vertices)
        glNormalPointer(GL_FLOAT, 0, normals)
        glDrawArrays(GL_TRIANGLES, 0, vertices.size // 3)
        glDisableClientState(GL_NORMAL_ARRAY)
        glDisableClientState(GL_VERTEX_ARRAY)

    def _draw_chain_end_caps(self, chain, all_points=None, frames=None, cap_segments=32):
        """
        Draw end caps only at the true start and end of the chain.

        Uses the parallel transport frames from tube rendering to ensure
        end cap orientation matches the tube exactly.
        Uses shape-aware caps that match the cross-section shape.
        """
        if not chain:
            return

        first_strand = chain[0]
        last_strand = chain[-1]

        # Use frames if provided (for consistent orientation with tube)
        if all_points is not None and frames is not None and len(all_points) >= 2 and len(frames) >= 2:
            # Start cap - use tangent from first two points (matches tube start)
            tangent_start = all_points[1] - all_points[0]
            tangent_len = np.linalg.norm(tangent_start)
            if tangent_len > 1e-6:
                tangent_start = tangent_start / tangent_len
            self._draw_shape_cap(
                first_strand.start,
                tangent_start,
                frame=frames[0],
                segments=cap_segments
            )

            # End cap - use tangent from last two points (matches tube end)
            tangent_end = all_points[-1] - all_points[-2]
            tangent_len = np.linalg.norm(tangent_end)
            if tangent_len > 1e-6:
                tangent_end = tangent_end / tangent_len
            self._draw_shape_cap(
                last_strand.end,
                tangent_end,
                frame=frames[-1],
                segments=cap_segments
            )
        else:
            # Fallback to original behavior if frames not provided
            tangent_start = first_strand.get_bezier_tangent(0.0)
            self._draw_shape_cap(first_strand.start, tangent_start, segments=cap_segments)

            tangent_end = last_strand.get_bezier_tangent(1.0)
            self._draw_shape_cap(last_strand.end, tangent_end, segments=cap_segments)

    def _draw_tube(self):
        """Draw the strand as a tube along the Bezier curve using parallel transport frame"""
        curve_points = self.get_curve_points()

        if len(curve_points) < 2:
            return

        # Build frames along the curve using parallel transport
        # This prevents twisting
        frames = self._compute_parallel_frames(curve_points)

        # Generate tube mesh
        for i in range(len(curve_points) - 1):
            p1 = curve_points[i]
            p2 = curve_points[i + 1]

            right1, up1 = frames[i]
            right2, up2 = frames[i + 1]

            # Generate cross-section vertices at each point (shape-aware)
            circle1 = self._get_circle_from_frame(p1, right1, up1)
            circle2 = self._get_circle_from_frame(p2, right2, up2)

            # Use actual vertex count (may vary by shape)
            num_verts = len(circle1)

            # Draw quad strip between circles
            glBegin(GL_QUAD_STRIP)
            for j in range(num_verts + 1):
                idx = j % num_verts

                # Normal is direction from center to vertex
                normal1 = circle1[idx] - p1
                norm_len1 = np.linalg.norm(normal1)
                if norm_len1 > 1e-6:
                    normal1 /= norm_len1

                normal2 = circle2[idx] - p2
                norm_len2 = np.linalg.norm(normal2)
                if norm_len2 > 1e-6:
                    normal2 /= norm_len2

                glNormal3f(*normal1)
                glVertex3f(*circle1[idx])

                glNormal3f(*normal2)
                glVertex3f(*circle2[idx])

            glEnd()

    def _compute_parallel_frames(self, points):
        """
        Compute parallel transport frames along the curve.
        This prevents the tube from twisting unexpectedly.

        Returns list of (right, up) tuples for each point.
        """
        frames = []

        # Initial frame at start
        tangent = points[1] - points[0]
        tangent_len = np.linalg.norm(tangent)
        if tangent_len > 1e-6:
            tangent /= tangent_len
        else:
            tangent = np.array([1.0, 0.0, 0.0])

        # Find initial perpendicular vectors
        if abs(tangent[1]) < 0.9:
            up_hint = np.array([0.0, 1.0, 0.0])
        else:
            up_hint = np.array([0.0, 0.0, 1.0])

        right = np.cross(tangent, up_hint)
        right_len = np.linalg.norm(right)
        if right_len > 1e-6:
            right /= right_len
        else:
            right = np.array([1.0, 0.0, 0.0])

        up = np.cross(right, tangent)
        up_len = np.linalg.norm(up)
        if up_len > 1e-6:
            up /= up_len

        frames.append((right.copy(), up.copy()))

        # Propagate frame along curve (parallel transport)
        for i in range(1, len(points)):
            if i < len(points) - 1:
                tangent_new = points[i + 1] - points[i]
            else:
                tangent_new = points[i] - points[i - 1]

            tangent_len = np.linalg.norm(tangent_new)
            if tangent_len > 1e-6:
                tangent_new /= tangent_len
            else:
                tangent_new = tangent.copy()

            # Rotate the frame to align with new tangent
            # Use reflection method for parallel transport
            v = tangent_new - tangent
            c = np.dot(tangent, tangent_new)

            if c > -0.99:  # Not opposite directions
                # Rodrigues rotation formula simplified
                right = right - (2.0 / (1.0 + c)) * np.dot(v, right) * (tangent + tangent_new) / 2.0

                # Re-orthogonalize
                right = right - np.dot(right, tangent_new) * tangent_new
                right_len = np.linalg.norm(right)
                if right_len > 1e-6:
                    right /= right_len

                up = np.cross(right, tangent_new)
                up_len = np.linalg.norm(up)
                if up_len > 1e-6:
                    up /= up_len

            tangent = tangent_new
            frames.append((right.copy(), up.copy()))

        return frames

    def _get_cross_section_points(self, num_segments):
        """
        Pre-compute cross-section profile points (offsets from center).
        Returns list of (x_factor, y_factor) tuples for each segment.
        These factors are multiplied by width*right and height*up respectively.
        """
        shape = getattr(self, 'cross_section_shape', 'ellipse')
        height_ratio = self.height_ratio

        points = []

        if shape == 'ellipse':
            for i in range(num_segments):
                angle = 2 * np.pi * i / num_segments
                points.append((np.cos(angle), np.sin(angle)))

        elif shape == 'circle':
            # Circle: use height_ratio of 1.0 effectively
            for i in range(num_segments):
                angle = 2 * np.pi * i / num_segments
                points.append((np.cos(angle), np.sin(angle)))
            # Override height_ratio for circle
            height_ratio = 1.0

        elif shape == 'rectangle':
            corner_radius = getattr(self, 'corner_radius', 0.0)
            if corner_radius <= 0:
                # Sharp rectangle - distribute points along edges
                segments_per_side = max(1, num_segments // 4)
                for side in range(4):
                    for j in range(segments_per_side):
                        t = j / segments_per_side
                        if side == 0:    # Top edge (right to left at top)
                            points.append((1.0 - 2*t, 1.0))
                        elif side == 1:  # Left edge
                            points.append((-1.0, 1.0 - 2*t))
                        elif side == 2:  # Bottom edge
                            points.append((-1.0 + 2*t, -1.0))
                        elif side == 3:  # Right edge
                            points.append((1.0, -1.0 + 2*t))
            else:
                # Rounded rectangle
                r = corner_radius
                segments_per_corner = max(2, num_segments // 8)
                segments_per_edge = max(1, num_segments // 8)
                corners = [(1-r, 1-r), (-1+r, 1-r), (-1+r, -1+r), (1-r, -1+r)]
                for ci, (cx, cy) in enumerate(corners):
                    start_angle = -np.pi/2 + ci * np.pi/2
                    for j in range(segments_per_corner):
                        angle = start_angle + j * (np.pi/2) / segments_per_corner
                        points.append((cx + r*np.cos(angle), cy + r*np.sin(angle)))
                    # Edge after corner
                    if ci == 0:  # Top edge
                        for j in range(segments_per_edge):
                            t = j / segments_per_edge
                            points.append(((1-r)*(1-t) + (-1+r)*t, 1.0))
                    elif ci == 1:  # Left edge
                        for j in range(segments_per_edge):
                            t = j / segments_per_edge
                            points.append((-1.0, (1-r)*(1-t) + (-1+r)*t))
                    elif ci == 2:  # Bottom edge
                        for j in range(segments_per_edge):
                            t = j / segments_per_edge
                            points.append(((-1+r)*(1-t) + (1-r)*t, -1.0))
                    elif ci == 3:  # Right edge
                        for j in range(segments_per_edge):
                            t = j / segments_per_edge
                            points.append((1.0, (-1+r)*(1-t) + (1-r)*t))

        elif shape == 'diamond':
            segments_per_side = max(1, num_segments // 4)
            for side in range(4):
                for j in range(segments_per_side):
                    t = j / segments_per_side
                    if side == 0:    # Top to right
                        points.append((t, 1.0 - t))
                    elif side == 1:  # Right to bottom
                        points.append((1.0 - t, -t))
                    elif side == 2:  # Bottom to left
                        points.append((-t, -1.0 + t))
                    elif side == 3:  # Left to top
                        points.append((-1.0 + t, t))

        elif shape == 'hexagon':
            for i in range(6):
                angle = np.pi/6 + i * np.pi/3
                points.append((np.cos(angle), np.sin(angle)))
            # Interpolate to get more segments
            if num_segments > 6:
                interpolated = []
                segments_per_side = max(1, num_segments // 6)
                for i in range(6):
                    p1 = points[i]
                    p2 = points[(i + 1) % 6]
                    for j in range(segments_per_side):
                        t = j / segments_per_side
                        interpolated.append((p1[0]*(1-t) + p2[0]*t, p1[1]*(1-t) + p2[1]*t))
                points = interpolated

        else:
            # Fallback to ellipse
            for i in range(num_segments):
                angle = 2 * np.pi * i / num_segments
                points.append((np.cos(angle), np.sin(angle)))

        return points, height_ratio

    def _get_ellipse_from_frame(self, center, right, up):
        """
        Get vertices of a cross-section shape using pre-computed frame vectors.
        Supports multiple shapes: ellipse, rectangle, circle, diamond, hexagon.

        - 'right' direction: full width
        - 'up' direction: reduced height (height_ratio * width)
        """
        vertices = []
        height = self.width * self.height_ratio
        shape = getattr(self, 'cross_section_shape', 'ellipse')

        if shape == 'ellipse' or shape == 'circle':
            # Ellipse/circle cross-section
            h = height if shape == 'ellipse' else self.width
            for i in range(self.tube_segments):
                angle = 2 * np.pi * i / self.tube_segments
                offset = (self.width * np.cos(angle) * right +
                         h * np.sin(angle) * up)
                vertices.append(center + offset)

        elif shape == 'rectangle':
            # Rectangle with optional rounded corners
            corner_radius = getattr(self, 'corner_radius', 0.0)
            vertices = self._get_rectangle_vertices(center, right, up, self.width, height, corner_radius)

        elif shape == 'diamond':
            # Diamond/rhombus shape (4 vertices, interpolated)
            segments_per_side = max(2, self.tube_segments // 4)
            # Top to right
            for i in range(segments_per_side):
                t = i / segments_per_side
                offset = ((1 - t) * 0 + t * self.width) * right + ((1 - t) * height + t * 0) * up
                vertices.append(center + offset)
            # Right to bottom
            for i in range(segments_per_side):
                t = i / segments_per_side
                offset = ((1 - t) * self.width + t * 0) * right + ((1 - t) * 0 + t * (-height)) * up
                vertices.append(center + offset)
            # Bottom to left
            for i in range(segments_per_side):
                t = i / segments_per_side
                offset = ((1 - t) * 0 + t * (-self.width)) * right + ((1 - t) * (-height) + t * 0) * up
                vertices.append(center + offset)
            # Left to top
            for i in range(segments_per_side):
                t = i / segments_per_side
                offset = ((1 - t) * (-self.width) + t * 0) * right + ((1 - t) * 0 + t * height) * up
                vertices.append(center + offset)

        elif shape == 'hexagon':
            # Hexagonal cross-section
            for i in range(6):
                angle = np.pi / 6 + i * np.pi / 3
                offset = self.width * np.cos(angle) * right + height * np.sin(angle) * up
                vertices.append(center + offset)
            # Interpolate to get smooth segments
            if self.tube_segments > 6:
                interpolated = []
                segments_per_side = max(1, self.tube_segments // 6)
                for i in range(6):
                    v1 = vertices[i]
                    v2 = vertices[(i + 1) % 6]
                    for j in range(segments_per_side):
                        t = j / segments_per_side
                        interpolated.append(v1 * (1 - t) + v2 * t)
                vertices = interpolated

        else:
            # Fallback to ellipse
            for i in range(self.tube_segments):
                angle = 2 * np.pi * i / self.tube_segments
                offset = (self.width * np.cos(angle) * right +
                         height * np.sin(angle) * up)
                vertices.append(center + offset)

        return vertices

    def _get_rectangle_vertices(self, center, right, up, width, height, corner_radius):
        """Generate vertices for a rectangle with optional rounded corners."""
        vertices = []

        if corner_radius <= 0:
            # Sharp corners - simple rectangle
            segments_per_side = max(2, self.tube_segments // 4)
            corners = [
                (width, height),    # Top-right
                (width, -height),   # Bottom-right
                (-width, -height),  # Bottom-left
                (-width, height),   # Top-left
            ]
            for i in range(4):
                c1 = corners[i]
                c2 = corners[(i + 1) % 4]
                for j in range(segments_per_side):
                    t = j / segments_per_side
                    x = c1[0] * (1 - t) + c2[0] * t
                    y = c1[1] * (1 - t) + c2[1] * t
                    offset = x * right + y * up
                    vertices.append(center + offset)
        else:
            # Rounded corners
            min_dim = min(width, height)
            r = corner_radius * min_dim  # Actual corner radius

            segments_per_corner = max(2, self.tube_segments // 8)
            segments_per_edge = max(1, self.tube_segments // 8)

            # Corner centers
            corners = [
                (width - r, height - r),    # Top-right
                (width - r, -height + r),   # Bottom-right
                (-width + r, -height + r),  # Bottom-left
                (-width + r, height - r),   # Top-left
            ]

            # Generate vertices going around the rectangle
            for i in range(4):
                # Corner arc
                start_angle = -np.pi / 2 + i * np.pi / 2
                cx, cy = corners[i]
                for j in range(segments_per_corner):
                    angle = start_angle + j * (np.pi / 2) / segments_per_corner
                    x = cx + r * np.cos(angle)
                    y = cy + r * np.sin(angle)
                    offset = x * right + y * up
                    vertices.append(center + offset)

                # Edge to next corner (straight part)
                next_corner = corners[(i + 1) % 4]
                # Determine edge direction
                if i == 0:  # Top-right to bottom-right (right edge)
                    for j in range(segments_per_edge):
                        t = j / segments_per_edge
                        y = (height - r) * (1 - t) + (-height + r) * t
                        offset = width * right + y * up
                        vertices.append(center + offset)
                elif i == 1:  # Bottom-right to bottom-left (bottom edge)
                    for j in range(segments_per_edge):
                        t = j / segments_per_edge
                        x = (width - r) * (1 - t) + (-width + r) * t
                        offset = x * right + (-height) * up
                        vertices.append(center + offset)
                elif i == 2:  # Bottom-left to top-left (left edge)
                    for j in range(segments_per_edge):
                        t = j / segments_per_edge
                        y = (-height + r) * (1 - t) + (height - r) * t
                        offset = (-width) * right + y * up
                        vertices.append(center + offset)
                elif i == 3:  # Top-left to top-right (top edge)
                    for j in range(segments_per_edge):
                        t = j / segments_per_edge
                        x = (-width + r) * (1 - t) + (width - r) * t
                        offset = x * right + height * up
                        vertices.append(center + offset)

        return vertices

    def _get_circle_from_frame(self, center, right, up):
        """
        Get vertices of a circle using pre-computed frame vectors.
        Now redirects to ellipse for plastic leather look.
        """
        return self._get_ellipse_from_frame(center, right, up)

    def _get_circle_vertices(self, center, tangent):
        """
        Get vertices of a circle perpendicular to the tangent.
        (Legacy method - kept for compatibility)
        """
        # Find perpendicular vectors
        if abs(tangent[1]) < 0.9:
            up = np.array([0.0, 1.0, 0.0])
        else:
            up = np.array([0.0, 0.0, 1.0])

        # Create perpendicular basis
        right = np.cross(tangent, up)
        right_len = np.linalg.norm(right)
        if right_len > 1e-6:
            right /= right_len

        up = np.cross(right, tangent)
        up_len = np.linalg.norm(up)
        if up_len > 1e-6:
            up /= up_len

        # Generate circle vertices
        vertices = []
        for i in range(self.tube_segments):
            angle = 2 * np.pi * i / self.tube_segments
            offset = self.width * (np.cos(angle) * right + np.sin(angle) * up)
            vertices.append(center + offset)

        return vertices

    def _draw_end_caps(self):
        """Draw end caps on the tube matching the cross-section shape"""
        tangent_start = self.get_bezier_tangent(0.0)
        tangent_end = self.get_bezier_tangent(1.0)

        # Draw both end caps using shape-aware method
        self._draw_shape_cap(self.start, tangent_start)
        self._draw_shape_cap(self.end, tangent_end)

    def _draw_shape_cap(self, position, tangent, frame=None, segments=32):
        """
        Draw an end cap matching the current cross-section shape.

        For ellipse/circle: draws a rounded ellipsoid cap
        For rectangle/diamond/hexagon: draws a flat cap matching the shape
        """
        shape = getattr(self, 'cross_section_shape', 'ellipse')

        # For ellipse and circle, use the rounded ellipsoid cap
        if shape in ('ellipse', 'circle'):
            if frame:
                self._draw_ellipsoid_cap_with_frame(position, tangent, frame, segments)
            else:
                self._draw_ellipsoid_cap(position, tangent, segments)
            return

        # For other shapes, draw a flat cap
        self._draw_flat_cap(position, tangent, frame)

    def _draw_flat_cap(self, position, tangent, frame=None):
        """
        Draw a flat end cap matching the cross-section shape.
        Used for rectangle, diamond, hexagon shapes.
        """
        # Normalize tangent
        tangent = np.array(tangent, dtype=float)
        tangent_len = np.linalg.norm(tangent)
        if tangent_len > 1e-6:
            tangent = tangent / tangent_len

        # Get frame vectors (right, up)
        if frame:
            right, up = frame
        else:
            # Compute frame if not provided
            if abs(tangent[1]) < 0.9:
                up_hint = np.array([0.0, 1.0, 0.0])
            else:
                up_hint = np.array([0.0, 0.0, 1.0])

            right = np.cross(tangent, up_hint)
            right_len = np.linalg.norm(right)
            if right_len > 1e-6:
                right /= right_len

            up = np.cross(right, tangent)
            up_len = np.linalg.norm(up)
            if up_len > 1e-6:
                up /= up_len

        # Get the cross-section vertices
        vertices = self._get_ellipse_from_frame(position, right, up)

        if len(vertices) < 3:
            return

        # Draw filled polygon for the cap
        # Use triangle fan from center
        glBegin(GL_TRIANGLE_FAN)

        # Normal points along tangent (outward from strand)
        glNormal3f(*tangent)

        # Center vertex
        glVertex3f(*position)

        # Perimeter vertices
        for v in vertices:
            glVertex3f(*v)

        # Close the fan
        glVertex3f(*vertices[0])

        glEnd()

    def _draw_ellipsoid_cap(self, position, tangent, segments=32):
        """Draw an ellipsoid cap at the given position, oriented along tangent"""
        glPushMatrix()
        glTranslatef(*position)

        # Calculate orientation to align with tangent
        # We need to rotate the ellipsoid so its long axis aligns with 'right' vector
        if abs(tangent[1]) < 0.9:
            up_hint = np.array([0.0, 1.0, 0.0])
        else:
            up_hint = np.array([0.0, 0.0, 1.0])

        right = np.cross(tangent, up_hint)
        right_len = np.linalg.norm(right)
        if right_len > 1e-6:
            right /= right_len

        up = np.cross(right, tangent)
        up_len = np.linalg.norm(up)
        if up_len > 1e-6:
            up /= up_len

        # Build rotation matrix (column vectors: right, up, tangent)
        rotation = np.array([
            [right[0], up[0], tangent[0], 0],
            [right[1], up[1], tangent[1], 0],
            [right[2], up[2], tangent[2], 0],
            [0, 0, 0, 1]
        ], dtype=np.float32)

        glMultMatrixf(rotation.T.flatten())

        # Scale to create ellipsoid: wide in X (right), flat in Y (up), short in Z (tangent)
        height = self.width * self.height_ratio
        glScalef(self.width, height, self.width * 0.5)  # Hemisphere depth

        # Enable normal renormalization for correct lighting after scaling
        glEnable(GL_NORMALIZE)

        quadric = gluNewQuadric()
        gluQuadricNormals(quadric, GLU_SMOOTH)  # Smooth normals for proper lighting
        gluSphere(quadric, 1.0, segments, segments)
        gluDeleteQuadric(quadric)

        glPopMatrix()

    def _draw_ellipsoid_cap_with_frame(self, position, tangent, frame, segments=32):
        """
        Draw an ellipsoid cap using a pre-computed frame for orientation.

        This ensures the cap orientation matches the tube exactly by using
        the same frame (right, up vectors) computed during parallel transport.

        Args:
            position: 3D position for the cap
            tangent: Tangent direction at this point
            frame: Tuple of (right, up) vectors from parallel transport
        """
        glPushMatrix()
        glTranslatef(*position)

        # Use the pre-computed frame vectors
        right, up = frame

        # Ensure tangent is normalized
        tangent = np.array(tangent, dtype=float)
        tangent_len = np.linalg.norm(tangent)
        if tangent_len > 1e-6:
            tangent = tangent / tangent_len

        # Build rotation matrix (column vectors: right, up, tangent)
        rotation = np.array([
            [right[0], up[0], tangent[0], 0],
            [right[1], up[1], tangent[1], 0],
            [right[2], up[2], tangent[2], 0],
            [0, 0, 0, 1]
        ], dtype=np.float32)

        glMultMatrixf(rotation.T.flatten())

        # Scale to create ellipsoid: wide in X (right), flat in Y (up), short in Z (tangent)
        height = self.width * self.height_ratio
        glScalef(self.width, height, self.width * 0.5)  # Hemisphere depth

        # Enable normal renormalization for correct lighting after scaling
        glEnable(GL_NORMALIZE)

        quadric = gluNewQuadric()
        gluQuadricNormals(quadric, GLU_SMOOTH)  # Smooth normals for proper lighting
        gluSphere(quadric, 1.0, segments, segments)
        gluDeleteQuadric(quadric)

        glPopMatrix()

    def _draw_sphere(self, position, radius):
        """Draw a sphere at the given position (legacy, now uses ellipsoid)"""
        glPushMatrix()
        glTranslatef(*position)

        # Scale to ellipsoid shape
        height = radius * self.height_ratio
        glScalef(radius, height, radius)

        # Enable normal renormalization for correct lighting after scaling
        glEnable(GL_NORMALIZE)

        quadric = gluNewQuadric()
        gluQuadricNormals(quadric, GLU_SMOOTH)  # Smooth normals for proper lighting
        gluSphere(quadric, 1.0, 32, 32)
        gluDeleteQuadric(quadric)

        glPopMatrix()

    # ==================== Control Point Methods ====================

    def get_default_control_points(self):
        """
        Calculate what the default control points would be for current start/end.
        Default is 1/3 and 2/3 along the direction from start to end.

        Returns:
            tuple: (cp1, cp2) numpy arrays
        """
        direction = self.end - self.start
        cp1 = self.start + direction * 0.33
        cp2 = self.start + direction * 0.67
        return cp1, cp2

    def is_control_points_default(self, tolerance=1e-4):
        """
        Check if control points are at their default positions (1/3 and 2/3 along strand).

        Args:
            tolerance: Maximum distance to consider as "default"

        Returns:
            bool: True if CPs are at default positions
        """
        expected_cp1, expected_cp2 = self.get_default_control_points()
        return (np.allclose(self.control_point1, expected_cp1, atol=tolerance) and
                np.allclose(self.control_point2, expected_cp2, atol=tolerance))

    def make_straight(self):
        """
        Set control points to make the strand a straight line.
        CPs are placed at 1/3 and 2/3 along the line from start to end.
        """
        direction = self.end - self.start
        self.control_point1 = self.start + direction * 0.33
        self.control_point2 = self.start + direction * 0.67
        self._mark_geometry_dirty()

    def save_control_points(self):
        """
        Save current control point state for later restoration.

        Returns:
            dict: Contains cp1, cp2 arrays and is_default flag
        """
        return {
            'cp1': self.control_point1.copy(),
            'cp2': self.control_point2.copy(),
            'is_default': self.is_control_points_default()
        }

    def restore_control_points(self, saved):
        """
        Restore control points from saved state.
        If saved state was default, recalculates default for current positions.

        Args:
            saved: dict from save_control_points() or None
        """
        if saved is None:
            # No saved state - use default
            self._init_control_points()
            return

        if saved.get('is_default', False):
            # Was default - recalculate default for current start/end
            self._init_control_points()
        else:
            # Was custom - restore exact positions
            self.control_point1 = saved['cp1'].copy()
            self.control_point2 = saved['cp2'].copy()
            self._mark_geometry_dirty()

    def set_control_point1(self, position, delta=None, link_cps=False):
        """
        Set the first control point position.

        Args:
            position: New CP1 position
            delta: Movement delta (if None, calculated from old position)
            link_cps: If True, sync connected CPs for C1 continuity (smooth spline)
        """
        old_cp1 = self.control_point1.copy() if delta is None else None
        self.control_point1 = np.array(position, dtype=float)
        self._mark_geometry_dirty()

        # Calculate delta if not provided
        if delta is None:
            delta = self.control_point1 - old_cp1

        # Only sync attached strands if link_cps is enabled
        if link_cps:
            # Sync attached strands at start (attachment_side == 0) using true C1 symmetry
            for attached in self.attached_strands:
                if hasattr(attached, 'attachment_side') and attached.attachment_side == 0:
                    if hasattr(attached, 'sync_cp1_with_parent_c1'):
                        attached.sync_cp1_with_parent_c1()

    def set_control_point2(self, position, delta=None, link_cps=False):
        """
        Set the second control point position.

        Args:
            position: New CP2 position
            delta: Movement delta (if None, calculated from old position)
            link_cps: If True, sync connected CPs for C1 continuity (smooth spline)
        """
        old_cp2 = self.control_point2.copy() if delta is None else None
        self.control_point2 = np.array(position, dtype=float)
        self._mark_geometry_dirty()

        # Calculate delta if not provided
        if delta is None:
            delta = self.control_point2 - old_cp2

        # Only sync attached strands if link_cps is enabled
        if link_cps:
            # Sync attached strands at end (attachment_side == 1) using true C1 symmetry
            for attached in self.attached_strands:
                if hasattr(attached, 'attachment_side') and attached.attachment_side == 1:
                    if hasattr(attached, 'sync_cp1_with_parent_c1'):
                        attached.sync_cp1_with_parent_c1()

    def set_start(self, position, link_cps=False):
        """
        Set the start position (2D-style: only move control points if coincident).

        Args:
            position: New start position
            link_cps: If True, sync connected CPs for C1 continuity
        """
        old_start = self.start.copy()
        new_start = np.array(position, dtype=float)

        # Only move control points if they coincide with the current start point
        # (matches 2D behavior from openstrand_1_106)
        if np.allclose(self.control_point1, old_start, atol=1e-6):
            self.control_point1 = new_start.copy()
        if np.allclose(self.control_point2, old_start, atol=1e-6):
            self.control_point2 = new_start.copy()

        self.start = new_start
        self._mark_geometry_dirty()

        # NOTE: Don't call update_start_from_parent() here - it moves the ENTIRE attached strand.
        # Instead, let _propagate_to_attached_strands in move_mode.py handle the 2D-style
        # propagation (only move the attached strand's start, not its end).

        # Only sync CPs if link_cps is enabled
        if link_cps:
            for attached in self.attached_strands:
                if hasattr(attached, 'attachment_side') and attached.attachment_side == 0:
                    if hasattr(attached, 'sync_cp1_with_parent_c1'):
                        attached.sync_cp1_with_parent_c1()

    def set_end(self, position, link_cps=False):
        """
        Set the end position (2D-style: only move control points if coincident).

        Args:
            position: New end position
            link_cps: If True, sync connected CPs for C1 continuity
        """
        old_end = self.end.copy()
        new_end = np.array(position, dtype=float)

        # Only move control points if they coincide with the current end point
        # (matches 2D behavior from openstrand_1_106)
        if np.allclose(self.control_point1, old_end, atol=1e-6):
            self.control_point1 = new_end.copy()
        if np.allclose(self.control_point2, old_end, atol=1e-6):
            self.control_point2 = new_end.copy()

        self.end = new_end
        self._mark_geometry_dirty()

        # NOTE: Don't call update_start_from_parent() here - it moves the ENTIRE attached strand.
        # Instead, let _propagate_to_attached_strands in move_mode.py handle the 2D-style
        # propagation (only move the attached strand's start, not its end).

        # Only sync CPs if link_cps is enabled
        if link_cps:
            for attached in self.attached_strands:
                if hasattr(attached, 'attachment_side') and attached.attachment_side == 1:
                    if hasattr(attached, 'sync_cp1_with_parent_c1'):
                        attached.sync_cp1_with_parent_c1()

    def move(self, delta):
        """Move the entire strand by delta"""
        delta = np.array(delta, dtype=float)
        self.start += delta
        self.end += delta
        self.control_point1 += delta
        self.control_point2 += delta
        self._mark_geometry_dirty()

    # ==================== Twist Angle Methods ====================

    def set_start_twist(self, angle):
        """Set the twist angle at the start point (in degrees)"""
        self.start_twist = float(angle)
        self._mark_geometry_dirty()

    def set_end_twist(self, angle):
        """Set the twist angle at the end point (in degrees)"""
        self.end_twist = float(angle)
        self._mark_geometry_dirty()

    def set_cp1_twist(self, angle):
        """Set the twist angle at control point 1 (in degrees)"""
        self.cp1_twist = float(angle)
        self._mark_geometry_dirty()

    def set_cp2_twist(self, angle):
        """Set the twist angle at control point 2 (in degrees)"""
        self.cp2_twist = float(angle)
        self._mark_geometry_dirty()

    def set_twist(self, point_name, angle):
        """
        Set twist angle for a specific point.

        Args:
            point_name: 'start', 'end', 'cp1', or 'cp2'
            angle: Twist angle in degrees
        """
        if point_name == 'start':
            self.set_start_twist(angle)
        elif point_name == 'end':
            self.set_end_twist(angle)
        elif point_name == 'cp1':
            self.set_cp1_twist(angle)
        elif point_name == 'cp2':
            self.set_cp2_twist(angle)

    def get_twist(self, point_name):
        """
        Get twist angle for a specific point.

        Args:
            point_name: 'start', 'end', 'cp1', or 'cp2'

        Returns:
            Twist angle in degrees
        """
        if point_name == 'start':
            return self.start_twist
        elif point_name == 'end':
            return self.end_twist
        elif point_name == 'cp1':
            return self.cp1_twist
        elif point_name == 'cp2':
            return self.cp2_twist
        return 0.0

    # ==================== Serialization ====================

    def to_dict(self):
        """Convert strand to dictionary for saving"""
        return {
            'name': self.name,
            'start': self.start.tolist(),
            'end': self.end.tolist(),
            'control_point1': self.control_point1.tolist(),
            'control_point2': self.control_point2.tolist(),
            'color': self.color,
            'width': self.width,
            'height_ratio': self.height_ratio,
            'cross_section_shape': getattr(self, 'cross_section_shape', 'ellipse'),
            'corner_radius': getattr(self, 'corner_radius', 0.0),
            'visible': self.visible,
            'start_twist': self.start_twist,
            'end_twist': self.end_twist,
            'cp1_twist': self.cp1_twist,
            'cp2_twist': self.cp2_twist
        }

    @classmethod
    def from_dict(cls, data):
        """Create strand from dictionary"""
        strand = cls(
            start=data['start'],
            end=data['end'],
            name=data.get('name', ''),
            color=tuple(data.get('color', (0.667, 0.667, 1.0, 1.0))),
            width=data.get('width', 0.15)
        )

        strand.control_point1 = np.array(data['control_point1'])
        strand.control_point2 = np.array(data['control_point2'])
        strand.height_ratio = data.get('height_ratio', 0.4)
        strand.cross_section_shape = data.get('cross_section_shape', 'ellipse')
        strand.corner_radius = data.get('corner_radius', 0.0)
        strand.visible = data.get('visible', True)

        # Load twist angles (default to 0 for backwards compatibility)
        strand.start_twist = data.get('start_twist', 0.0)
        strand.end_twist = data.get('end_twist', 0.0)
        strand.cp1_twist = data.get('cp1_twist', 0.0)
        strand.cp2_twist = data.get('cp2_twist', 0.0)

        strand._mark_geometry_dirty()

        return strand

    def __repr__(self):
        return f"Strand(name='{self.name}', start={self.start}, end={self.end})"
