bl_info = {
    "name": "Hair Cards UV Tools",
    "author": "YoruAnimation",
    "version": (1, 0, 0),
    "blender": (5, 0, 0),
    "location": "UV Editor > Sidebar > Hair Cards",
    "description": "Tools for selecting quad islands and straightening hair card UVs",
    "category": "UV",
}


import bpy
import bmesh
import math
from mathutils import Vector


# ============================================================
# COMMON POPUP
# ============================================================

def show_message(message, title="Hair Cards", icon='INFO'):

    def draw(self, context):
        self.layout.label(text=message)

    bpy.context.window_manager.popup_menu(
        draw,
        title=title,
        icon=icon
    )


# ============================================================
# TOOL 1
# SELECT 100% QUAD ISLANDS
# ============================================================

class UV_OT_select_quad_islands(bpy.types.Operator):

    bl_idname = "uv.select_quad_islands"
    bl_label = "Select Quad Islands"
    bl_description = "Select only UV islands made entirely of quads"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):

        obj = context.edit_object

        if obj is None or obj.type != 'MESH':

            self.report(
                {'WARNING'},
                "Select a mesh and enter Edit Mode"
            )

            return {'CANCELLED'}

        bm = bmesh.from_edit_mesh(
            obj.data
        )

        uv_layer = (
            bm.loops.layers.uv.active
        )

        if uv_layer is None:

            self.report(
                {'WARNING'},
                "No active UV Map found"
            )

            return {'CANCELLED'}

        EPS = 1e-6


        # ----------------------------------------------------
        # UV CONNECTION CHECK
        # ----------------------------------------------------

        def uv_close(a, b):

            return (
                a - b
            ).length < EPS


        def faces_uv_connected(
            face_a,
            face_b
        ):

            shared_edges = (
                set(face_a.edges)
                .intersection(
                    face_b.edges
                )
            )

            for edge in shared_edges:

                verts = list(
                    edge.verts
                )

                uv_a = {}
                uv_b = {}

                for loop in face_a.loops:

                    if loop.vert in verts:

                        uv_a[
                            loop.vert
                        ] = (
                            loop[
                                uv_layer
                            ].uv.copy()
                        )

                for loop in face_b.loops:

                    if loop.vert in verts:

                        uv_b[
                            loop.vert
                        ] = (
                            loop[
                                uv_layer
                            ].uv.copy()
                        )

                if (
                    len(uv_a) != 2
                    or len(uv_b) != 2
                ):
                    continue

                connected = all(
                    vert in uv_b
                    and uv_close(
                        uv_a[vert],
                        uv_b[vert]
                    )
                    for vert in uv_a
                )

                if connected:
                    return True

            return False


        # ----------------------------------------------------
        # DETECT UV ISLANDS
        # ----------------------------------------------------

        all_faces = list(
            bm.faces
        )

        remaining = set(
            all_faces
        )

        islands = []

        while remaining:

            start = (
                remaining.pop()
            )

            island = {
                start
            }

            stack = [
                start
            ]

            while stack:

                current = (
                    stack.pop()
                )

                for edge in current.edges:

                    for linked in edge.link_faces:

                        if linked not in remaining:
                            continue

                        if faces_uv_connected(
                            current,
                            linked
                        ):

                            remaining.remove(
                                linked
                            )

                            island.add(
                                linked
                            )

                            stack.append(
                                linked
                            )

            islands.append(
                list(island)
            )


        # ----------------------------------------------------
        # DESELECT EVERYTHING
        # ----------------------------------------------------

        for face in bm.faces:
            face.select = False


        # ----------------------------------------------------
        # SELECT ONLY 100% QUAD ISLANDS
        # ----------------------------------------------------

        selected_islands = 0

        for island in islands:

            only_quads = all(
                len(face.verts) == 4
                for face in island
            )

            if not only_quads:
                continue

            for face in island:
                face.select = True

            selected_islands += 1


        bmesh.update_edit_mesh(
            obj.data,
            loop_triangles=False,
            destructive=False
        )


        self.report(
            {'INFO'},
            f"{selected_islands} quad island(s) selected"
        )

        return {'FINISHED'}


# ============================================================
# TOOL
# ALIGN UV ISLANDS VERTICALLY
# WORKS WITH QUADS, TRIANGLES AND N-GONS
# ============================================================

class UV_OT_align_islands_vertical(bpy.types.Operator):

    bl_idname = "uv.align_islands_vertical"
    bl_label = "Align Islands Vertical"
    bl_description = (
        "Rotate selected UV islands so their main axis "
        "is aligned vertically"
    )
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):

        obj = context.edit_object

        if obj is None or obj.type != 'MESH':

            self.report(
                {'WARNING'},
                "Select a mesh and enter Edit Mode"
            )

            return {'CANCELLED'}

        mesh = obj.data
        bm = bmesh.from_edit_mesh(mesh)

        uv_layer = bm.loops.layers.uv.active

        if uv_layer is None:

            self.report(
                {'WARNING'},
                "No active UV Map found"
            )

            return {'CANCELLED'}


        selected_faces = [
            face
            for face in bm.faces
            if face.select
        ]

        if not selected_faces:

            self.report(
                {'WARNING'},
                "No faces selected"
            )

            return {'CANCELLED'}


        EPS = 1e-6


        # ====================================================
        # UV CONNECTION
        # ====================================================

        def uv_close(a, b):

            return (
                a - b
            ).length < EPS


        def faces_uv_connected(
            face_a,
            face_b
        ):

            shared_edges = (
                set(face_a.edges)
                .intersection(
                    face_b.edges
                )
            )

            for edge in shared_edges:

                edge_verts = list(
                    edge.verts
                )

                uv_a = {}
                uv_b = {}


                for loop in face_a.loops:

                    if loop.vert in edge_verts:

                        uv_a[
                            loop.vert
                        ] = (
                            loop[
                                uv_layer
                            ].uv.copy()
                        )


                for loop in face_b.loops:

                    if loop.vert in edge_verts:

                        uv_b[
                            loop.vert
                        ] = (
                            loop[
                                uv_layer
                            ].uv.copy()
                        )


                if (
                    len(uv_a) != 2
                    or len(uv_b) != 2
                ):
                    continue


                if all(
                    vert in uv_b
                    and uv_close(
                        uv_a[vert],
                        uv_b[vert]
                    )
                    for vert in uv_a
                ):

                    return True


            return False


        # ====================================================
        # DETECT SELECTED UV ISLANDS
        # ====================================================

        selected_set = set(
            selected_faces
        )

        remaining = set(
            selected_faces
        )

        islands = []


        while remaining:

            start = remaining.pop()

            island = {
                start
            }

            stack = [
                start
            ]


            while stack:

                current = stack.pop()

                for edge in current.edges:

                    for linked in edge.link_faces:

                        if linked not in remaining:
                            continue

                        if linked not in selected_set:
                            continue

                        if faces_uv_connected(
                            current,
                            linked
                        ):

                            remaining.remove(
                                linked
                            )

                            island.add(
                                linked
                            )

                            stack.append(
                                linked
                            )


            islands.append(
                list(island)
            )


        # ====================================================
        # UNIQUE UV POINTS
        # ====================================================

        def get_unique_uv_points(island):

            points = []

            for face in island:

                for loop in face.loops:

                    uv = (
                        loop[
                            uv_layer
                        ].uv.copy()
                    )


                    if not any(
                        (
                            uv - existing
                        ).length < EPS

                        for existing in points
                    ):

                        points.append(
                            uv
                        )

            return points


        # ====================================================
        # CALCULATE PRINCIPAL AXIS
        #
        # 2D PCA:
        # finds the direction in which the UV island
        # has the greatest spread.
        # ====================================================

        def get_principal_axis(points):

            if len(points) < 2:
                return None


            center = Vector((
                sum(
                    p.x
                    for p in points
                ) / len(points),

                sum(
                    p.y
                    for p in points
                ) / len(points)
            ))


            xx = 0.0
            xy = 0.0
            yy = 0.0


            for point in points:

                offset = (
                    point -
                    center
                )

                xx += (
                    offset.x
                    *
                    offset.x
                )

                xy += (
                    offset.x
                    *
                    offset.y
                )

                yy += (
                    offset.y
                    *
                    offset.y
                )


            xx /= len(points)
            xy /= len(points)
            yy /= len(points)


            # ----------------------------------------------
            # Largest eigenvector of the 2x2 covariance
            # matrix.
            # ----------------------------------------------

            trace = (
                xx + yy
            )

            determinant = (
                xx * yy
                -
                xy * xy
            )


            discriminant = max(
                0.0,
                trace * trace * 0.25
                -
                determinant
            )


            eigenvalue = (
                trace * 0.5
                +
                discriminant ** 0.5
            )


            if abs(xy) > 1e-10:

                axis = Vector((
                    eigenvalue - yy,
                    xy
                ))

            elif xx >= yy:

                axis = Vector((
                    1.0,
                    0.0
                ))

            else:

                axis = Vector((
                    0.0,
                    1.0
                ))


            if axis.length <= 1e-10:
                return None


            axis.normalize()

            return (
                center,
                axis
            )


        # ====================================================
        # ROTATE ISLAND
        # ====================================================

        def rotate_island_to_vertical(
            island
        ):

            points = (
                get_unique_uv_points(
                    island
                )
            )


            result = (
                get_principal_axis(
                    points
                )
            )


            if result is None:
                return False


            center, axis = result


            # ----------------------------------------------
            # Make the main axis point upward
            # ----------------------------------------------

            if axis.y < 0.0:

                axis *= -1.0


            # ----------------------------------------------
            # Angle needed to align axis with +Y
            # ----------------------------------------------

            angle = math.atan2(
                axis.x,
                axis.y
            )


            cos_a = math.cos(
                angle
            )

            sin_a = math.sin(
                angle
            )


            # ----------------------------------------------
            # Rotate around island center
            # ----------------------------------------------

            for face in island:

                for loop in face.loops:

                    uv = (
                        loop[
                            uv_layer
                        ].uv
                    )

                    offset = (
                        uv -
                        center
                    )


                    x = (
                        offset.x
                        *
                        cos_a
                        -
                        offset.y
                        *
                        sin_a
                    )

                    y = (
                        offset.x
                        *
                        sin_a
                        +
                        offset.y
                        *
                        cos_a
                    )


                    uv.x = (
                        center.x + x
                    )

                    uv.y = (
                        center.y + y
                    )


            return True


        # ====================================================
        # PROCESS
        # ====================================================

        aligned = 0
        skipped = 0


        for island in islands:

            if rotate_island_to_vertical(
                island
            ):

                aligned += 1

            else:

                skipped += 1


        # ====================================================
        # UPDATE
        # ====================================================

        bmesh.update_edit_mesh(
            mesh,
            loop_triangles=False,
            destructive=False
        )


        self.report(
            {'INFO'},
            (
                f"{aligned} island(s) aligned vertically"
                +
                (
                    f" | {skipped} skipped"
                    if skipped > 0
                    else ""
                )
            )
        )


        return {'FINISHED'}


# ============================================================
# TOOL
# ALIGN UV ISLANDS HORIZONTALLY
# WORKS WITH QUADS, TRIANGLES AND N-GONS
# ============================================================

class UV_OT_align_islands_horizontal(bpy.types.Operator):

    bl_idname = "uv.align_islands_horizontal"
    bl_label = "Align Islands Horizontal"
    bl_description = (
        "Rotate selected UV islands so their main axis "
        "is aligned horizontally"
    )
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):

        obj = context.edit_object

        if obj is None or obj.type != 'MESH':

            self.report(
                {'WARNING'},
                "Select a mesh and enter Edit Mode"
            )

            return {'CANCELLED'}

        mesh = obj.data
        bm = bmesh.from_edit_mesh(mesh)

        uv_layer = bm.loops.layers.uv.active

        if uv_layer is None:

            self.report(
                {'WARNING'},
                "No active UV Map found"
            )

            return {'CANCELLED'}


        selected_faces = [
            face
            for face in bm.faces
            if face.select
        ]

        if not selected_faces:

            self.report(
                {'WARNING'},
                "No faces selected"
            )

            return {'CANCELLED'}


        EPS = 1e-6


        # ====================================================
        # UV CONNECTION
        # ====================================================

        def uv_close(a, b):

            return (
                a - b
            ).length < EPS


        def faces_uv_connected(
            face_a,
            face_b
        ):

            shared_edges = (
                set(face_a.edges)
                .intersection(
                    face_b.edges
                )
            )

            for edge in shared_edges:

                edge_verts = list(
                    edge.verts
                )

                uv_a = {}
                uv_b = {}


                for loop in face_a.loops:

                    if loop.vert in edge_verts:

                        uv_a[
                            loop.vert
                        ] = (
                            loop[
                                uv_layer
                            ].uv.copy()
                        )


                for loop in face_b.loops:

                    if loop.vert in edge_verts:

                        uv_b[
                            loop.vert
                        ] = (
                            loop[
                                uv_layer
                            ].uv.copy()
                        )


                if (
                    len(uv_a) != 2
                    or len(uv_b) != 2
                ):
                    continue


                if all(
                    vert in uv_b
                    and uv_close(
                        uv_a[vert],
                        uv_b[vert]
                    )
                    for vert in uv_a
                ):

                    return True


            return False


        # ====================================================
        # DETECT SELECTED UV ISLANDS
        # ====================================================

        selected_set = set(
            selected_faces
        )

        remaining = set(
            selected_faces
        )

        islands = []


        while remaining:

            start = remaining.pop()

            island = {
                start
            }

            stack = [
                start
            ]

            while stack:

                current = stack.pop()

                for edge in current.edges:

                    for linked in edge.link_faces:

                        if linked not in remaining:
                            continue

                        if linked not in selected_set:
                            continue

                        if faces_uv_connected(
                            current,
                            linked
                        ):

                            remaining.remove(
                                linked
                            )

                            island.add(
                                linked
                            )

                            stack.append(
                                linked
                            )


            islands.append(
                list(island)
            )


        # ====================================================
        # UNIQUE UV POINTS
        # ====================================================

        def get_unique_uv_points(island):

            points = []

            for face in island:

                for loop in face.loops:

                    uv = (
                        loop[
                            uv_layer
                        ].uv.copy()
                    )

                    if not any(
                        (
                            uv - existing
                        ).length < EPS

                        for existing in points
                    ):

                        points.append(
                            uv
                        )

            return points


        # ====================================================
        # PRINCIPAL AXIS
        # ====================================================

        def get_principal_axis(points):

            if len(points) < 2:
                return None


            center = Vector((
                sum(
                    p.x
                    for p in points
                ) / len(points),

                sum(
                    p.y
                    for p in points
                ) / len(points)
            ))


            xx = 0.0
            xy = 0.0
            yy = 0.0


            for point in points:

                offset = (
                    point -
                    center
                )

                xx += (
                    offset.x
                    *
                    offset.x
                )

                xy += (
                    offset.x
                    *
                    offset.y
                )

                yy += (
                    offset.y
                    *
                    offset.y
                )


            xx /= len(points)
            xy /= len(points)
            yy /= len(points)


            trace = (
                xx + yy
            )

            determinant = (
                xx * yy
                -
                xy * xy
            )


            discriminant = max(
                0.0,
                trace * trace * 0.25
                -
                determinant
            )


            eigenvalue = (
                trace * 0.5
                +
                discriminant ** 0.5
            )


            if abs(xy) > 1e-10:

                axis = Vector((
                    eigenvalue - yy,
                    xy
                ))

            elif xx >= yy:

                axis = Vector((
                    1.0,
                    0.0
                ))

            else:

                axis = Vector((
                    0.0,
                    1.0
                ))


            if axis.length <= 1e-10:
                return None


            axis.normalize()

            return (
                center,
                axis
            )


        # ====================================================
        # ROTATE ISLAND TO HORIZONTAL
        # ====================================================

        def rotate_island_to_horizontal(
            island
        ):

            points = (
                get_unique_uv_points(
                    island
                )
            )


            result = (
                get_principal_axis(
                    points
                )
            )


            if result is None:
                return False


            center, axis = result


            # ------------------------------------------------
            # Keep the principal axis pointing toward +X
            # ------------------------------------------------

            if axis.x < 0.0:

                axis *= -1.0


            # ------------------------------------------------
            # Rotate the axis onto +X
            #
            # atan2(y, x) gives the current angle
            # of the principal axis.
            # ------------------------------------------------

            angle = -math.atan2(
                axis.y,
                axis.x
            )


            cos_a = math.cos(
                angle
            )

            sin_a = math.sin(
                angle
            )


            # ------------------------------------------------
            # ROTATE AROUND ISLAND CENTER
            # ------------------------------------------------

            for face in island:

                for loop in face.loops:

                    uv = (
                        loop[
                            uv_layer
                        ].uv
                    )

                    offset = (
                        uv -
                        center
                    )


                    x = (
                        offset.x
                        *
                        cos_a
                        -
                        offset.y
                        *
                        sin_a
                    )

                    y = (
                        offset.x
                        *
                        sin_a
                        +
                        offset.y
                        *
                        cos_a
                    )


                    uv.x = (
                        center.x + x
                    )

                    uv.y = (
                        center.y + y
                    )


            return True


        # ====================================================
        # PROCESS
        # ====================================================

        aligned = 0
        skipped = 0


        for island in islands:

            if rotate_island_to_horizontal(
                island
            ):

                aligned += 1

            else:

                skipped += 1


        # ====================================================
        # UPDATE
        # ====================================================

        bmesh.update_edit_mesh(
            mesh,
            loop_triangles=False,
            destructive=False
        )


        self.report(
            {'INFO'},
            (
                f"{aligned} island(s) aligned horizontally"
                +
                (
                    f" | {skipped} skipped"
                    if skipped > 0
                    else ""
                )
            )
        )


        return {'FINISHED'}

    # ============================================================
# TOOL
# MATCH UV ISLAND LOCATION TO ACTIVE ISLAND
# ============================================================

class UV_OT_match_island_location(bpy.types.Operator):

    bl_idname = "uv.match_island_location"
    bl_label = "Match Island Location"
    bl_description = (
        "Move selected UV islands to the location "
        "of the UV island containing the active face"
    )
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):

        obj = context.edit_object

        if obj is None or obj.type != 'MESH':

            self.report(
                {'WARNING'},
                "Select a mesh and enter Edit Mode"
            )

            return {'CANCELLED'}

        mesh = obj.data

        bm = bmesh.from_edit_mesh(
            mesh
        )

        uv_layer = (
            bm.loops.layers.uv.active
        )

        if uv_layer is None:

            self.report(
                {'WARNING'},
                "No active UV Map found"
            )

            return {'CANCELLED'}


        # ====================================================
        # ACTIVE FACE = REFERENCE
        # ====================================================

        active_face = (
            bm.faces.active
        )

        if (
            active_face is None
            or not active_face.select
        ):

            self.report(
                {'WARNING'},
                "Select an active reference face"
            )

            return {'CANCELLED'}


        selected_faces = [
            face
            for face in bm.faces
            if face.select
        ]

        if not selected_faces:

            self.report(
                {'WARNING'},
                "No faces selected"
            )

            return {'CANCELLED'}


        # ====================================================
        # UV CONNECTION HELPERS
        # ====================================================

        EPS = 1e-6


        def uv_close(a, b):

            return (
                a - b
            ).length < EPS


        def faces_uv_connected(
            face_a,
            face_b
        ):

            shared_edges = (
                set(face_a.edges)
                .intersection(
                    face_b.edges
                )
            )

            for edge in shared_edges:

                verts = list(
                    edge.verts
                )

                uv_a = {}
                uv_b = {}


                for loop in face_a.loops:

                    if loop.vert in verts:

                        uv_a[
                            loop.vert
                        ] = (
                            loop[
                                uv_layer
                            ].uv.copy()
                        )


                for loop in face_b.loops:

                    if loop.vert in verts:

                        uv_b[
                            loop.vert
                        ] = (
                            loop[
                                uv_layer
                            ].uv.copy()
                        )


                if (
                    len(uv_a) != 2
                    or len(uv_b) != 2
                ):
                    continue


                if all(
                    vert in uv_b
                    and uv_close(
                        uv_a[vert],
                        uv_b[vert]
                    )
                    for vert in uv_a
                ):

                    return True

            return False


        # ====================================================
        # GET UV ISLAND
        # ====================================================

        def get_island(
            start_face,
            allowed_faces
        ):

            allowed_set = set(
                allowed_faces
            )

            island = {
                start_face
            }

            stack = [
                start_face
            ]

            while stack:

                current = (
                    stack.pop()
                )

                for edge in current.edges:

                    for linked in edge.link_faces:

                        if (
                            linked not in allowed_set
                            or linked in island
                        ):
                            continue

                        if faces_uv_connected(
                            current,
                            linked
                        ):

                            island.add(
                                linked
                            )

                            stack.append(
                                linked
                            )

            return list(
                island
            )


        # ====================================================
        # DETECT SELECTED UV ISLANDS
        # ====================================================

        remaining = set(
            selected_faces
        )

        islands = []

        while remaining:

            start = next(
                iter(remaining)
            )

            island = get_island(
                start,
                remaining
            )

            for face in island:

                remaining.discard(
                    face
                )

            islands.append(
                island
            )


        # ====================================================
        # FIND REFERENCE ISLAND
        # ====================================================

        reference_island = None

        for island in islands:

            if active_face in island:

                reference_island = (
                    island
                )

                break


        if reference_island is None:

            self.report(
                {'WARNING'},
                "Could not find reference UV island"
            )

            return {'CANCELLED'}


        # ====================================================
        # GET ISLAND CENTER
        # ====================================================

        def get_island_center(island):

            uvs = []

            for face in island:

                for loop in face.loops:

                    uvs.append(
                        loop[
                            uv_layer
                        ].uv.copy()
                    )

            if not uvs:

                return None


            min_x = min(
                uv.x
                for uv in uvs
            )

            max_x = max(
                uv.x
                for uv in uvs
            )

            min_y = min(
                uv.y
                for uv in uvs
            )

            max_y = max(
                uv.y
                for uv in uvs
            )


            return Vector((
                (
                    min_x +
                    max_x
                ) * 0.5,

                (
                    min_y +
                    max_y
                ) * 0.5
            ))


        # ====================================================
        # REFERENCE LOCATION
        # ====================================================

        reference_center = (
            get_island_center(
                reference_island
            )
        )

        if reference_center is None:

            self.report(
                {'WARNING'},
                "Reference island has no valid UV coordinates"
            )

            return {'CANCELLED'}


        # ====================================================
        # MOVE OTHER ISLANDS
        # ====================================================

        moved = 0


        for island in islands:

            if island is reference_island:
                continue


            island_center = (
                get_island_center(
                    island
                )
            )

            if island_center is None:
                continue


            offset = (
                reference_center -
                island_center
            )


            for face in island:

                for loop in face.loops:

                    loop[
                        uv_layer
                    ].uv += offset


            moved += 1


        # ====================================================
        # UPDATE
        # ====================================================

        bmesh.update_edit_mesh(
            mesh,
            loop_triangles=False,
            destructive=False
        )


        self.report(
            {'INFO'},
            f"{moved} island(s) moved to reference location"
        )


        return {'FINISHED'}


# ============================================================
# TOOL 2
# STRAIGHTEN HAIR CARDS
# ============================================================

class UV_OT_straighten_hair_cards(
    bpy.types.Operator
):

    bl_idname = "uv.straighten_hair_cards"
    bl_label = "Straighten Hair Cards"
    bl_description = "Straighten selected quad hair card UV islands"
    bl_options = {'REGISTER', 'UNDO'}


    def execute(self, context):

        obj = context.edit_object

        if obj is None or obj.type != 'MESH':

            self.report(
                {'WARNING'},
                "Select a mesh and enter Edit Mode"
            )

            return {'CANCELLED'}


        mesh = obj.data

        bm = bmesh.from_edit_mesh(
            mesh
        )

        uv_layer = (
            bm.loops.layers.uv.active
        )


        if uv_layer is None:

            self.report(
                {'WARNING'},
                "No active UV Map found"
            )

            return {'CANCELLED'}


        selected_faces = [
            face
            for face in bm.faces
            if face.select
        ]


        if not selected_faces:

            self.report(
                {'WARNING'},
                "No faces selected"
            )

            return {'CANCELLED'}


        # ====================================================
        # HELPER FUNCTIONS
        # ====================================================

        def island_is_100_percent_quads(
            island
        ):

            return all(
                len(face.verts) == 4
                for face in island
            )


        def get_island_bbox_center(
            island
        ):

            uvs = []

            for face in island:

                for loop in face.loops:

                    uvs.append(
                        loop[
                            uv_layer
                        ].uv.copy()
                    )

            min_x = min(
                uv.x
                for uv in uvs
            )

            max_x = max(
                uv.x
                for uv in uvs
            )

            min_y = min(
                uv.y
                for uv in uvs
            )

            max_y = max(
                uv.y
                for uv in uvs
            )

            return Vector((
                (
                    min_x
                    + max_x
                ) * 0.5,

                (
                    min_y
                    + max_y
                ) * 0.5
            ))


        def uv_face_area(face):

            loops = list(
                face.loops
            )

            if len(loops) != 4:
                return 0.0

            uvs = [
                loop[
                    uv_layer
                ].uv.copy()
                for loop in loops
            ]

            def triangle_area(
                a,
                b,
                c
            ):

                ab = b - a
                ac = c - a

                return abs(
                    ab.x * ac.y
                    -
                    ab.y * ac.x
                ) * 0.5


            return (
                triangle_area(
                    uvs[0],
                    uvs[1],
                    uvs[2]
                )
                +
                triangle_area(
                    uvs[0],
                    uvs[2],
                    uvs[3]
                )
            )


        def straighten_reference_quad(
            face
        ):

            loops = list(
                face.loops
            )

            if len(loops) != 4:
                return False

            uvs = [
                loop[
                    uv_layer
                ].uv.copy()
                for loop in loops
            ]

            center = sum(
                uvs,
                Vector(
                    (0.0, 0.0)
                )
            ) / 4.0


            lengths = []

            for i in range(4):

                lengths.append(
                    (
                        uvs[
                            (i + 1) % 4
                        ]
                        -
                        uvs[i]
                    ).length
                )


            if min(lengths) < 1e-8:
                return False


            pair_a = (
                lengths[0]
                + lengths[2]
            ) * 0.5

            pair_b = (
                lengths[1]
                + lengths[3]
            ) * 0.5


            length = max(
                pair_a,
                pair_b
            )

            width = min(
                pair_a,
                pair_b
            )


            width = max(
                width,
                0.0001
            )

            length = max(
                length,
                0.0001
            )


            if pair_a >= pair_b:

                new_uvs = [

                    Vector((
                        center.x
                        - width * 0.5,

                        center.y
                        - length * 0.5
                    )),

                    Vector((
                        center.x
                        - width * 0.5,

                        center.y
                        + length * 0.5
                    )),

                    Vector((
                        center.x
                        + width * 0.5,

                        center.y
                        + length * 0.5
                    )),

                    Vector((
                        center.x
                        + width * 0.5,

                        center.y
                        - length * 0.5
                    )),
                ]

            else:

                new_uvs = [

                    Vector((
                        center.x
                        - width * 0.5,

                        center.y
                        + length * 0.5
                    )),

                    Vector((
                        center.x
                        + width * 0.5,

                        center.y
                        + length * 0.5
                    )),

                    Vector((
                        center.x
                        + width * 0.5,

                        center.y
                        - length * 0.5
                    )),

                    Vector((
                        center.x
                        - width * 0.5,

                        center.y
                        - length * 0.5
                    )),
                ]


            for loop, uv in zip(
                loops,
                new_uvs
            ):

                loop[
                    uv_layer
                ].uv = uv


            return True


        def force_island_vertical(
            island
        ):

            uv_loops = []

            for face in island:

                for loop in face.loops:

                    uv_loops.append(
                        loop[
                            uv_layer
                        ]
                    )


            xs = [
                luv.uv.x
                for luv in uv_loops
            ]

            ys = [
                luv.uv.y
                for luv in uv_loops
            ]


            min_x = min(xs)
            max_x = max(xs)

            min_y = min(ys)
            max_y = max(ys)


            width = (
                max_x
                - min_x
            )

            height = (
                max_y
                - min_y
            )


            if height >= width:
                return


            center = Vector((
                (
                    min_x
                    + max_x
                ) * 0.5,

                (
                    min_y
                    + max_y
                ) * 0.5
            ))


            for luv in uv_loops:

                offset = (
                    luv.uv
                    - center
                )

                rotated = Vector((
                    -offset.y,
                    offset.x
                ))

                luv.uv = (
                    center
                    + rotated
                )


        # ====================================================
        # FIND UV EDITOR
        # ====================================================

        uv_area = None
        uv_region = None

        for area in context.screen.areas:

            if area.type == 'IMAGE_EDITOR':

                uv_area = area

                for region in area.regions:

                    if region.type == 'WINDOW':

                        uv_region = region
                        break

                if uv_region:
                    break


        if (
            uv_area is None
            or uv_region is None
        ):

            self.report(
                {'WARNING'},
                "Open a UV Editor first"
            )

            return {'CANCELLED'}


        # ====================================================
        # DETECT CONNECTED SELECTED ISLANDS
        # ====================================================

        selected_set = set(
            selected_faces
        )

        remaining = set(
            selected_faces
        )

        islands = []


        while remaining:

            start = (
                remaining.pop()
            )

            island = {
                start
            }

            stack = [
                start
            ]

            while stack:

                face = (
                    stack.pop()
                )

                for edge in face.edges:

                    for linked in edge.link_faces:

                        if (
                            linked in remaining
                            and
                            linked in selected_set
                        ):

                            remaining.remove(
                                linked
                            )

                            island.add(
                                linked
                            )

                            stack.append(
                                linked
                            )

            islands.append(
                list(island)
            )


        original_face_indices = {
            face.index
            for face in selected_faces
        }


        processed = 0
        skipped = 0
        errors = 0


        # ====================================================
        # PROCESS
        # ====================================================

        for index, island in enumerate(
            islands
        ):


            # ------------------------------------------------
            # 100% QUAD SAFETY
            # ------------------------------------------------

            if not island_is_100_percent_quads(
                island
            ):

                skipped += 1
                continue


            island_indices = [
                face.index
                for face in island
            ]


            original_center = (
                get_island_bbox_center(
                    island
                )
            )


            # ------------------------------------------------
            # SELECT CURRENT ISLAND ONLY
            # ------------------------------------------------

            for face in bm.faces:
                face.select = False

            for face in island:
                face.select = True


            # ------------------------------------------------
            # FIND END FACES
            # ------------------------------------------------

            island_set = set(
                island
            )

            end_faces = []


            for face in island:

                neighbors = 0

                for edge in face.edges:

                    for linked in edge.link_faces:

                        if (
                            linked != face
                            and
                            linked in island_set
                        ):

                            neighbors += 1

                if neighbors == 1:

                    end_faces.append(
                        face
                    )


            # ------------------------------------------------
            # CHOOSE LARGEST END QUAD
            # ------------------------------------------------

            if end_faces:

                active_face = max(
                    end_faces,
                    key=uv_face_area
                )

            else:

                active_face = max(
                    island,
                    key=uv_face_area
                )


            bm.faces.active = (
                active_face
            )


            # ------------------------------------------------
            # STRAIGHTEN REFERENCE QUAD
            # ------------------------------------------------

            if not straighten_reference_quad(
                active_face
            ):

                errors += 1
                continue


            bmesh.update_edit_mesh(
                mesh,
                loop_triangles=False,
                destructive=False
            )


            # ------------------------------------------------
            # FOLLOW ACTIVE QUADS
            # ------------------------------------------------

            try:

                with context.temp_override(
                    area=uv_area,
                    region=uv_region,
                    active_object=obj,
                    object=obj,
                    edit_object=obj
                ):

                    bpy.ops.uv.follow_active_quads(
                        mode='LENGTH_AVERAGE'
                    )


            except Exception:

                errors += 1
                continue


            # ------------------------------------------------
            # REFRESH BMESH
            # ------------------------------------------------

            bm = bmesh.from_edit_mesh(
                mesh
            )

            bm.faces.ensure_lookup_table()

            uv_layer = (
                bm.loops.layers.uv.active
            )


            island = [
                bm.faces[i]
                for i in island_indices
            ]


            # ------------------------------------------------
            # FORCE VERTICAL
            # ------------------------------------------------

            force_island_vertical(
                island
            )


            # ------------------------------------------------
            # RESTORE ORIGINAL POSITION
            # ------------------------------------------------

            new_center = (
                get_island_bbox_center(
                    island
                )
            )


            offset = (
                original_center
                -
                new_center
            )


            for face in island:

                for loop in face.loops:

                    loop[
                        uv_layer
                    ].uv += offset


            bmesh.update_edit_mesh(
                mesh,
                loop_triangles=False,
                destructive=False
            )


            processed += 1


        # ====================================================
        # RESTORE ORIGINAL SELECTION
        # ====================================================

        bm = bmesh.from_edit_mesh(
            mesh
        )

        bm.faces.ensure_lookup_table()


        for face in bm.faces:

            face.select = (
                face.index
                in original_face_indices
            )


        bmesh.update_edit_mesh(
            mesh,
            loop_triangles=False,
            destructive=False
        )


        self.report(
            {'INFO'},
            (
                f"{processed} straightened | "
                f"{skipped} skipped | "
                f"{errors} error(s)"
            )
        )


        return {'FINISHED'}


# ============================================================
# FORCE STRAIGHTEN HAIR CARDS
# ============================================================

class UV_OT_force_straighten_hair_cards(bpy.types.Operator):

    bl_idname = "uv.force_straighten_hair_cards"
    bl_label = "Force Straighten Hair Cards"
    bl_description = (
        "Force straighten selected hair card UV islands "
        "column by column. Supports quads and triangles."
    )
    bl_options = {'REGISTER', 'UNDO'}


    # ========================================================
    # UV HELPERS
    # ========================================================

    @staticmethod
    def uv_close(a, b):

        return (
            a - b
        ).length < 1e-6


    @staticmethod
    def get_vertex_uv(
        vert,
        island,
        uv_layer
    ):

        for face in island:

            if vert not in face.verts:
                continue

            for loop in face.loops:

                if loop.vert == vert:

                    return (
                        loop[
                            uv_layer
                        ].uv.copy()
                    )

        return None


    @staticmethod
    def set_vertex_uv_x(
        vert,
        island,
        uv_layer,
        x
    ):

        for face in island:

            if vert not in face.verts:
                continue

            for loop in face.loops:

                if loop.vert == vert:

                    loop[
                        uv_layer
                    ].uv.x = x


    # ========================================================
    # UV CONNECTIVITY
    # ========================================================

    def faces_uv_connected(
        self,
        face_a,
        face_b,
        uv_layer
    ):

        shared_edges = (
            set(face_a.edges)
            .intersection(
                face_b.edges
            )
        )


        for edge in shared_edges:

            edge_verts = set(
                edge.verts
            )

            uv_a = {}
            uv_b = {}


            for loop in face_a.loops:

                if loop.vert in edge_verts:

                    uv_a[
                        loop.vert
                    ] = (
                        loop[
                            uv_layer
                        ].uv.copy()
                    )


            for loop in face_b.loops:

                if loop.vert in edge_verts:

                    uv_b[
                        loop.vert
                    ] = (
                        loop[
                            uv_layer
                        ].uv.copy()
                    )


            if (
                len(uv_a) != 2
                or len(uv_b) != 2
            ):
                continue


            if all(
                vert in uv_b
                and self.uv_close(
                    uv_a[vert],
                    uv_b[vert]
                )
                for vert in uv_a
            ):

                return True


        return False


    # ========================================================
    # SELECTED UV ISLANDS
    # ========================================================

    def get_selected_islands(
        self,
        selected_faces,
        uv_layer
    ):

        remaining = set(
            selected_faces
        )

        islands = []


        while remaining:

            start = next(
                iter(remaining)
            )

            remaining.remove(
                start
            )

            island = {
                start
            }

            stack = [
                start
            ]


            while stack:

                current = (
                    stack.pop()
                )

                for edge in current.edges:

                    for linked in edge.link_faces:

                        if linked not in remaining:
                            continue


                        if self.faces_uv_connected(
                            current,
                            linked,
                            uv_layer
                        ):

                            remaining.remove(
                                linked
                            )

                            island.add(
                                linked
                            )

                            stack.append(
                                linked
                            )


            islands.append(
                list(island)
            )


        return islands


    # ========================================================
    # VALIDATION
    # ========================================================

    @staticmethod
    def validate_island(island):

        for face in island:

            corner_count = len(
                face.verts
            )


            if corner_count > 4:

                return False, (
                    "N-gon detected"
                )


            if corner_count < 3:

                return False, (
                    "Invalid face detected"
                )


        return True, None


    # ========================================================
    # ROTATE ISLAND VERTICALLY
    # ========================================================

    @staticmethod
    def rotate_island_vertical(
        island,
        uv_layer
    ):

        uv_points = []


        for face in island:

            for loop in face.loops:

                uv_points.append(
                    loop[
                        uv_layer
                    ].uv.copy()
                )


        if len(uv_points) < 2:
            return False


        # ----------------------------------------------------
        # ISLAND CENTER
        # ----------------------------------------------------

        center = Vector((

            sum(
                uv.x
                for uv in uv_points
            ) / len(uv_points),

            sum(
                uv.y
                for uv in uv_points
            ) / len(uv_points)

        ))


        # ----------------------------------------------------
        # PRINCIPAL AXIS / PCA
        # ----------------------------------------------------

        xx = 0.0
        xy = 0.0
        yy = 0.0


        for uv in uv_points:

            offset = (
                uv - center
            )

            xx += (
                offset.x *
                offset.x
            )

            xy += (
                offset.x *
                offset.y
            )

            yy += (
                offset.y *
                offset.y
            )


        count = len(
            uv_points
        )

        xx /= count
        xy /= count
        yy /= count


        trace = (
            xx + yy
        )

        determinant = (
            xx * yy
            -
            xy * xy
        )

        discriminant = max(
            0.0,
            trace * trace * 0.25
            -
            determinant
        )

        eigenvalue = (
            trace * 0.5
            +
            discriminant ** 0.5
        )


        if abs(xy) > 1e-6:

            axis = Vector((

                eigenvalue - yy,
                xy

            ))

        elif xx >= yy:

            axis = Vector((
                1.0,
                0.0
            ))

        else:

            axis = Vector((
                0.0,
                1.0
            ))


        if axis.length <= 1e-6:
            return False


        axis.normalize()


        if axis.y < 0.0:
            axis *= -1.0


        # ----------------------------------------------------
        # ROTATE TO +Y
        # ----------------------------------------------------

        angle = math.atan2(
            axis.x,
            axis.y
        )

        cos_a = math.cos(
            angle
        )

        sin_a = math.sin(
            angle
        )


        for face in island:

            for loop in face.loops:

                uv = (
                    loop[
                        uv_layer
                    ].uv
                )

                offset = (
                    uv - center
                )


                x = (
                    offset.x *
                    cos_a
                    -
                    offset.y *
                    sin_a
                )

                y = (
                    offset.x *
                    sin_a
                    +
                    offset.y *
                    cos_a
                )


                uv.x = (
                    center.x + x
                )

                uv.y = (
                    center.y + y
                )


        return True


    # ========================================================
    # BOUNDARY
    # ========================================================

    @staticmethod
    def get_boundary_edges(island):

        island_set = set(
            island
        )

        boundary = []


        for face in island:

            for edge in face.edges:

                linked_inside = [

                    linked
                    for linked in edge.link_faces
                    if linked in island_set

                ]


                if len(linked_inside) == 1:

                    if edge not in boundary:

                        boundary.append(
                            edge
                        )


        return boundary


    @staticmethod
    def build_boundary_loop(
        boundary_edges
    ):

        adjacency = {}


        for edge in boundary_edges:

            a, b = edge.verts

            adjacency.setdefault(
                a,
                []
            ).append(b)

            adjacency.setdefault(
                b,
                []
            ).append(a)


        if len(adjacency) < 4:
            return None


        if any(
            len(neighbors) != 2
            for neighbors
            in adjacency.values()
        ):

            return None


        start = next(
            iter(adjacency)
        )

        ordered = [
            start
        ]

        previous = None
        current = start


        while True:

            neighbors = (
                adjacency[
                    current
                ]
            )


            if previous is None:

                next_vert = (
                    neighbors[0]
                )

            else:

                next_vert = (
                    neighbors[0]
                    if neighbors[0]
                    != previous
                    else neighbors[1]
                )


            if next_vert == start:
                break


            if next_vert in ordered:
                return None


            ordered.append(
                next_vert
            )

            previous = (
                current
            )

            current = (
                next_vert
            )


            if len(ordered) > len(adjacency):
                return None


        if len(ordered) != len(adjacency):
            return None


        return ordered


    # ========================================================
    # PATH LENGTH
    # ========================================================

    def path_length(
        self,
        vertices,
        island,
        uv_layer
    ):

        total = 0.0


        for index in range(
            len(vertices) - 1
        ):

            uv_a = (
                self.get_vertex_uv(
                    vertices[index],
                    island,
                    uv_layer
                )
            )

            uv_b = (
                self.get_vertex_uv(
                    vertices[
                        index + 1
                    ],
                    island,
                    uv_layer
                )
            )


            if (
                uv_a is None
                or uv_b is None
            ):
                continue


            total += (
                uv_b -
                uv_a
            ).length


        return total


    # ========================================================
    # FIND BOTH CARD ENDS
    # ========================================================

    def find_end_vertices(
        self,
        boundary,
        island,
        uv_layer
    ):

        count = len(
            boundary
        )

        best_pair = None
        best_score = -1.0


        for i in range(count):

            for j in range(
                i + 2,
                count
            ):

                if (
                    i == 0
                    and j == count - 1
                ):
                    continue


                path_a = []

                k = i


                while True:

                    path_a.append(
                        boundary[k]
                    )

                    if k == j:
                        break

                    k = (
                        k + 1
                    ) % count


                path_b = []

                k = i


                while True:

                    path_b.append(
                        boundary[k]
                    )

                    if k == j:
                        break

                    k = (
                        k - 1
                    ) % count


                length_a = (
                    self.path_length(
                        path_a,
                        island,
                        uv_layer
                    )
                )

                length_b = (
                    self.path_length(
                        path_b,
                        island,
                        uv_layer
                    )
                )


                if (
                    length_a <= 1e-6
                    or length_b <= 1e-6
                ):
                    continue


                balance = (
                    min(
                        length_a,
                        length_b
                    )
                    /
                    max(
                        length_a,
                        length_b
                    )
                )


                uv_i = (
                    self.get_vertex_uv(
                        boundary[i],
                        island,
                        uv_layer
                    )
                )

                uv_j = (
                    self.get_vertex_uv(
                        boundary[j],
                        island,
                        uv_layer
                    )
                )


                if (
                    uv_i is None
                    or uv_j is None
                ):
                    continue


                distance = (
                    uv_j -
                    uv_i
                ).length


                score = (
                    distance
                    *
                    (
                        0.35
                        +
                        balance * 0.65
                    )
                )


                if score > best_score:

                    best_score = (
                        score
                    )

                    best_pair = (
                        i,
                        j
                    )


        return best_pair


    # ========================================================
    # SPLIT OUTER COLUMNS
    # ========================================================

    @staticmethod
    def split_boundary_columns(
        boundary,
        start_index,
        end_index
    ):

        count = len(
            boundary
        )


        side_a = []

        index = (
            start_index
        )


        while True:

            side_a.append(
                boundary[index]
            )

            if index == end_index:
                break

            index = (
                index + 1
            ) % count


        side_b = []

        index = (
            start_index
        )


        while True:

            side_b.append(
                boundary[index]
            )

            if index == end_index:
                break

            index = (
                index - 1
            ) % count


        return (
            side_a,
            side_b
        )


    # ========================================================
    # X / SX0
    # ========================================================

    def get_average_x(
        self,
        vertices,
        island,
        uv_layer
    ):

        values = []


        for vert in vertices:

            uv = (
                self.get_vertex_uv(
                    vert,
                    island,
                    uv_layer
                )
            )

            if uv is not None:

                values.append(
                    uv.x
                )


        if not values:
            return None


        return (
            sum(values)
            /
            len(values)
        )


    def straighten_column_x(
        self,
        vertices,
        island,
        uv_layer
    ):

        if len(vertices) < 2:
            return None


        target_x = (
            self.get_average_x(
                vertices,
                island,
                uv_layer
            )
        )


        if target_x is None:
            return None


        for vert in vertices:

            self.set_vertex_uv_x(
                vert,
                island,
                uv_layer,
                target_x
            )


        return target_x


    # ========================================================
    # EDGE UTILITIES
    # ========================================================

    @staticmethod
    def find_edge_between(
        vert_a,
        vert_b
    ):

        for edge in vert_a.link_edges:

            if vert_b in edge.verts:
                return edge

        return None


    def column_vertices_to_edges(
        self,
        column
    ):

        edges = set()


        for index in range(
            len(column) - 1
        ):

            edge = (
                self.find_edge_between(
                    column[index],
                    column[
                        index + 1
                    ]
                )
            )

            if edge is not None:

                edges.add(
                    edge
                )


        return edges


    @staticmethod
    def edges_to_vertices(edges):

        vertices = set()


        for edge in edges:

            vertices.update(
                edge.verts
            )


        return list(
            vertices
        )


    # ========================================================
    # OPPOSITE EDGE
    # ========================================================

    @staticmethod
    def get_opposite_edge(
        face,
        edge
    ):

        if len(face.verts) != 4:
            return None


        current_vertices = set(
            edge.verts
        )


        for candidate in face.edges:

            if candidate == edge:
                continue


            if not (
                set(candidate.verts)
                &
                current_vertices
            ):

                return candidate


        return None


    # ========================================================
    # COLUMN VALIDATION
    # ========================================================

    @staticmethod
    def validate_column_edges(
        edges
    ):

        if not edges:
            return False


        adjacency = {}


        for edge in edges:

            for vert in edge.verts:

                adjacency.setdefault(
                    vert,
                    []
                ).append(edge)


        # No branching.
        if any(
            len(linked_edges) > 2
            for linked_edges
            in adjacency.values()
        ):

            return False


        endpoints = [

            vert
            for vert, linked_edges
            in adjacency.items()
            if len(linked_edges) == 1

        ]


        if len(endpoints) != 2:
            return False


        start = (
            endpoints[0]
        )

        visited_edges = set()
        visited_vertices = {
            start
        }

        stack = [
            start
        ]


        while stack:

            vert = (
                stack.pop()
            )


            for edge in adjacency.get(
                vert,
                []
            ):

                if edge in visited_edges:
                    continue


                visited_edges.add(
                    edge
                )


                a, b = (
                    edge.verts
                )

                other = (
                    b
                    if a == vert
                    else a
                )


                if other not in visited_vertices:

                    visited_vertices.add(
                        other
                    )

                    stack.append(
                        other
                    )


        return (
            len(visited_edges)
            ==
            len(edges)
        )


    # ========================================================
    # NEXT COLUMN
    # ========================================================

    def get_next_column_edges(
        self,
        current_edges,
        island,
        previous_edges
    ):

        island_set = set(
            island
        )

        candidates = set()


        for edge in current_edges:

            for face in edge.link_faces:

                if face not in island_set:
                    continue


                # Only quads propagate.
                if len(face.verts) != 4:
                    continue


                opposite = (
                    self.get_opposite_edge(
                        face,
                        edge
                    )
                )


                if opposite is None:
                    continue


                if opposite in previous_edges:
                    continue


                candidates.add(
                    opposite
                )


        if not candidates:
            return set()


        # Current column vertices.
        current_vertices = set()


        for edge in current_edges:

            current_vertices.update(
                edge.verts
            )


        clean_candidates = set()


        for edge in candidates:

            # Adjacent columns must not
            # collapse into the same vertices.
            if (
                set(edge.verts)
                &
                current_vertices
            ):
                continue


            clean_candidates.add(
                edge
            )


        if not clean_candidates:
            return set()


        if not self.validate_column_edges(
            clean_candidates
        ):

            return set()


        return clean_candidates


    # ========================================================
    # TRIANGLE TIPS
    # ========================================================

    @staticmethod
    def find_triangle_tips(
        island
    ):

        island_set = set(
            island
        )

        tips = []


        for face in island:

            if len(face.verts) != 3:
                continue


            for vert in face.verts:

                linked_inside = [

                    linked
                    for linked in vert.link_faces
                    if linked in island_set

                ]


                # Real terminal point.
                if len(linked_inside) != 1:
                    continue


                others = [

                    candidate
                    for candidate in face.verts
                    if candidate != vert

                ]


                if len(others) == 2:

                    tips.append(
                        (
                            vert,
                            others[0],
                            others[1]
                        )
                    )


        return tips


    def center_triangle_tips(
        self,
        tips,
        island,
        uv_layer
    ):

        centered = 0


        for (
            tip,
            vert_a,
            vert_b
        ) in tips:

            uv_a = (
                self.get_vertex_uv(
                    vert_a,
                    island,
                    uv_layer
                )
            )

            uv_b = (
                self.get_vertex_uv(
                    vert_b,
                    island,
                    uv_layer
                )
            )


            if (
                uv_a is None
                or uv_b is None
            ):
                continue


            target_x = (
                uv_a.x +
                uv_b.x
            ) * 0.5


            self.set_vertex_uv_x(
                tip,
                island,
                uv_layer,
                target_x
            )


            centered += 1


        return centered


    # ========================================================
    # LEFT -> RIGHT PROCESS
    # ========================================================

    def process_columns(
        self,
        left_column,
        right_column,
        island,
        uv_layer
    ):

        current_edges = (
            self.column_vertices_to_edges(
                left_column
            )
        )

        right_edges = (
            self.column_vertices_to_edges(
                right_column
            )
        )


        if not current_edges:

            return 0


        processed_edges = set()
        previous_edges = set()

        columns = 0

        max_iterations = (
            len(island) + 10
        )


        for _ in range(
            max_iterations
        ):

            current_edges = {

                edge
                for edge in current_edges
                if edge not in processed_edges

            }


            if not current_edges:
                break


            if not self.validate_column_edges(
                current_edges
            ):

                break


            current_vertices = (
                self.edges_to_vertices(
                    current_edges
                )
            )


            if len(current_vertices) < 2:
                break


            result = (
                self.straighten_column_x(
                    current_vertices,
                    island,
                    uv_layer
                )
            )


            if result is None:
                break


            columns += 1


            processed_edges.update(
                current_edges
            )


            if current_edges & right_edges:
                break


            next_edges = (
                self.get_next_column_edges(
                    current_edges,
                    island,
                    previous_edges
                )
            )


            next_edges = {

                edge
                for edge in next_edges
                if edge not in processed_edges

            }


            if not next_edges:
                break


            previous_edges = set(
                current_edges
            )

            current_edges = (
                next_edges
            )


        # ----------------------------------------------------
        # RIGHT BOUNDARY FALLBACK
        # ----------------------------------------------------

        if not (
            right_edges
            &
            processed_edges
        ):

            result = (
                self.straighten_column_x(
                    right_column,
                    island,
                    uv_layer
                )
            )


            if result is not None:
                columns += 1


        return columns


    # ========================================================
    # PROCESS ONE ISLAND
    # ========================================================

    def straighten_island(
        self,
        island,
        uv_layer
    ):

        valid, error = (
            self.validate_island(
                island
            )
        )


        if not valid:
            return False, error


        # ----------------------------------------------------
        # ALIGN VERTICAL FIRST
        # ----------------------------------------------------

        if not self.rotate_island_vertical(
            island,
            uv_layer
        ):

            return False, (
                "Could not align vertically"
            )


        # ----------------------------------------------------
        # BOUNDARY
        # ----------------------------------------------------

        boundary_edges = (
            self.get_boundary_edges(
                island
            )
        )

        boundary = (
            self.build_boundary_loop(
                boundary_edges
            )
        )


        if boundary is None:

            return False, (
                "Invalid boundary"
            )


        # ----------------------------------------------------
        # CARD ENDS
        # ----------------------------------------------------

        end_pair = (
            self.find_end_vertices(
                boundary,
                island,
                uv_layer
            )
        )


        if end_pair is None:

            return False, (
                "Could not detect card ends"
            )


        start_index, end_index = (
            end_pair
        )


        side_a, side_b = (
            self.split_boundary_columns(
                boundary,
                start_index,
                end_index
            )
        )


        # ----------------------------------------------------
        # LEFT / RIGHT
        # ----------------------------------------------------

        x_a = (
            self.get_average_x(
                side_a,
                island,
                uv_layer
            )
        )

        x_b = (
            self.get_average_x(
                side_b,
                island,
                uv_layer
            )
        )


        if (
            x_a is None
            or x_b is None
        ):

            return False, (
                "Could not detect left/right sides"
            )


        if x_a <= x_b:

            left_column = side_a
            right_column = side_b

        else:

            left_column = side_b
            right_column = side_a


        # ----------------------------------------------------
        # STRAIGHTEN COLUMNS
        # ----------------------------------------------------

        columns = (
            self.process_columns(
                left_column,
                right_column,
                island,
                uv_layer
            )
        )


        # ----------------------------------------------------
        # TRIANGLE TIPS
        # ----------------------------------------------------

        tips = (
            self.find_triangle_tips(
                island
            )
        )

        centered_tips = (
            self.center_triangle_tips(
                tips,
                island,
                uv_layer
            )
        )


        print(
            f"Columns={columns} | "
            f"Tips={centered_tips}"
        )


        return True, None


    # ========================================================
    # EXECUTE
    # ========================================================

    def execute(
        self,
        context
    ):

        obj = (
            context.edit_object
        )


        # ----------------------------------------------------
        # OBJECT
        # ----------------------------------------------------

        if (
            obj is None
            or obj.type != 'MESH'
        ):

            self.report(
                {'WARNING'},
                "Select a mesh and enter Edit Mode"
            )

            return {'CANCELLED'}


        mesh = (
            obj.data
        )

        bm = (
            bmesh.from_edit_mesh(
                mesh
            )
        )

        uv_layer = (
            bm.loops.layers.uv.active
        )


        if uv_layer is None:

            self.report(
                {'WARNING'},
                "No active UV Map found"
            )

            return {'CANCELLED'}


        # ----------------------------------------------------
        # SELECTION
        # ----------------------------------------------------

        selected_faces = [

            face
            for face in bm.faces
            if face.select

        ]


        if not selected_faces:

            self.report(
                {'WARNING'},
                "No faces selected"
            )

            return {'CANCELLED'}


        # ----------------------------------------------------
        # FIND ALL SELECTED ISLANDS
        # ----------------------------------------------------

        islands = (
            self.get_selected_islands(
                selected_faces,
                uv_layer
            )
        )


        if not islands:

            self.report(
                {'WARNING'},
                "No UV islands found"
            )

            return {'CANCELLED'}


        processed = 0
        skipped = 0


        # ====================================================
        # PROCESS ALL ISLANDS
        # ====================================================

        for island in islands:

            try:

                success, error = (
                    self.straighten_island(
                        island,
                        uv_layer
                    )
                )


                if success:

                    processed += 1

                else:

                    skipped += 1

                    print(
                        "Force Straighten skipped:",
                        error
                    )


            except Exception as error:

                skipped += 1

                print(
                    "Force Straighten error:",
                    error
                )


        # ----------------------------------------------------
        # UPDATE
        # ----------------------------------------------------

        bmesh.update_edit_mesh(
            mesh,
            loop_triangles=False,
            destructive=False
        )


        # ----------------------------------------------------
        # REPORT
        # ----------------------------------------------------

        if processed == 0:

            self.report(
                {'WARNING'},
                (
                    f"No islands processed | "
                    f"{skipped} skipped"
                )
            )

            return {'CANCELLED'}


        if skipped:

            self.report(
                {'INFO'},
                (
                    f"{processed} island(s) straightened | "
                    f"{skipped} skipped"
                )
            )

        else:

            self.report(
                {'INFO'},
                (
                    f"{processed} island(s) "
                    "force straightened successfully"
                )
            )


        return {'FINISHED'}


# ============================================================
# UV EDITOR PANEL
# ============================================================

class UV_PT_hair_cards_tools(
    bpy.types.Panel
):

    bl_label = "Hair Cards Tools"

    bl_idname = (
        "UV_PT_hair_cards_tools"
    )

    bl_space_type = (
        'IMAGE_EDITOR'
    )

    bl_region_type = (
        'UI'
    )

    bl_category = (
        "Hair Cards"
    )


    def draw(self, context):

        layout = self.layout


        # ----------------------------------------------------
        # SELECTION
        # ----------------------------------------------------

        box = layout.box()

        box.label(
            text="Selection"
        )

        box.operator(
            "uv.select_quad_islands",
            text="Select Quad Islands",
            icon='RESTRICT_SELECT_OFF'
        )

        
        # ----------------------------------------------------
        # align_islands
        # ----------------------------------------------------

        box = layout.box()
        
        box.label(
            text="Align islands"
        )

        row = box.row(align=True)

        row.operator(
        "uv.align_islands_vertical",
        text="Vertical",
        icon='TRIA_UP'
        )

        row.operator(
        "uv.align_islands_horizontal",
        text="Horizontal",
        icon='TRIA_RIGHT'
        )

        # ----------------------------------------------------
        # UV TOOLS
        # ----------------------------------------------------

        box = layout.box()

        box.label(
            text="UV"
        )

        box.operator(
            "uv.straighten_hair_cards",
            text="Straighten Cards",
            icon='UV'
        )

        box.operator(
            "uv.force_straighten_hair_cards",
            text="Force Straighten Cards",
            icon='MOD_SIMPLEDEFORM'
        )
        

        
        # ----------------------------------------------------
        # Match Island
        # ----------------------------------------------------

        box = layout.box()
        
        box.label(
            text="Match Island"
        )

        box.operator(
        "uv.match_island_size",
        text="Match Size",
        icon='FULLSCREEN_ENTER'
        )

        box.operator(
        "uv.match_island_location",
        text="Match Location",
        icon='PIVOT_BOUNDBOX'
        )


        # ----------------------------------------------------
        # Other
        # ----------------------------------------------------

        box = layout.box()

        box.label(
            text="Other"
        )

        box.operator(
            "object.qremesh_selected_cards",
            text="Remesh multiples",
            icon='MOD_REMESH'
        )

        box.label(
            text="Requires QRemeshify",
            icon='INFO'
        )


# ============================================================
# TOOL 3
# QREMESH SELECTED CARDS
# ============================================================

class OBJECT_OT_qremesh_selected_cards(
    bpy.types.Operator
):

    bl_idname = "object.qremesh_selected_cards"
    bl_label = "QRemesh Selected Cards"
    bl_description = "Remesh selected hair cards one by one using QRemeshify"
    bl_options = {'REGISTER', 'UNDO'}


    def execute(self, context):

        # ----------------------------------------------------
        # CHECK IF QREMESHIFY IS AVAILABLE
        # ----------------------------------------------------

        if not hasattr(
            bpy.ops,
            "qremeshify"
        ):

            self.report(
                {'WARNING'},
                "QRemeshify is required to use this option."
            )

            return {'CANCELLED'}


        if not hasattr(
            bpy.ops.qremeshify,
            "remesh"
        ):

            self.report(
                {'WARNING'},
                "QRemeshify is required to use this option."
            )

            return {'CANCELLED'}


        # ----------------------------------------------------
        # OBJECT MODE REQUIRED
        # ----------------------------------------------------

        if context.mode != 'OBJECT':

            try:

                bpy.ops.object.mode_set(
                    mode='OBJECT'
                )

            except Exception:

                self.report(
                    {'WARNING'},
                    "Switch to Object Mode before using QRemesh Selected Cards."
                )

                return {'CANCELLED'}


        # ----------------------------------------------------
        # STORE SELECTED MESH OBJECTS
        # ----------------------------------------------------

        objects_to_remesh = [
            obj
            for obj in context.selected_objects
            if obj.type == 'MESH'
        ]


        if not objects_to_remesh:

            self.report(
                {'WARNING'},
                "No mesh objects selected."
            )

            return {'CANCELLED'}


        print("--------------------------------")
        print("QRemesh batch started")
        print(
            "Objects:",
            len(objects_to_remesh)
        )
        print("--------------------------------")


        results = []
        errors = 0


        # ====================================================
        # PROCESS ONE OBJECT AT A TIME
        # ====================================================

        for index, source_obj in enumerate(
            objects_to_remesh
        ):

            print(
                f"Remeshing "
                f"{index + 1}/"
                f"{len(objects_to_remesh)}: "
                f"{source_obj.name}"
            )


            # ------------------------------------------------
            # DESELECT EVERYTHING
            # ------------------------------------------------

            bpy.ops.object.select_all(
                action='DESELECT'
            )


            # ------------------------------------------------
            # SELECT CURRENT CARD ONLY
            # ------------------------------------------------

            try:

                source_obj.hide_set(
                    False
                )

                source_obj.select_set(
                    True
                )

                context.view_layer.objects.active = (
                    source_obj
                )


            except Exception as error:

                print(
                    f"Selection error on "
                    f"{source_obj.name}:",
                    error
                )

                errors += 1
                continue


            # ------------------------------------------------
            # RUN QREMESHIFY
            # ------------------------------------------------

            try:

                result = (
                    bpy.ops.qremeshify.remesh()
                )

                print(
                    "QRemesh result:",
                    result
                )


            except Exception as error:

                print(
                    f"QRemesh error on "
                    f"{source_obj.name}:",
                    error
                )

                errors += 1
                continue


            # ------------------------------------------------
            # GET CREATED OBJECT
            # ------------------------------------------------

            new_obj = (
                context.view_layer.objects.active
            )


            if (
                new_obj is not None
                and
                new_obj != source_obj
            ):

                results.append(
                    new_obj
                )

                print(
                    "Created:",
                    new_obj.name
                )

            else:

                print(
                    f"Warning: no remeshed object "
                    f"detected for {source_obj.name}"
                )

                errors += 1


        # ====================================================
        # SELECT ALL RESULTS
        # ====================================================

        bpy.ops.object.select_all(
            action='DESELECT'
        )


        for obj in results:

            if (
                obj is not None
                and
                obj.name in bpy.data.objects
            ):

                obj.hide_set(
                    False
                )

                obj.select_set(
                    True
                )


        if results:

            context.view_layer.objects.active = (
                results[-1]
            )


        # ====================================================
        # FINAL REPORT
        # ====================================================

        print("--------------------------------")
        print("QRemesh batch completed")
        print(
            "Successful:",
            len(results)
        )
        print(
            "Errors:",
            errors
        )
        print("--------------------------------")


        if errors > 0:

            self.report(
                {'WARNING'},
                (
                    f"{len(results)} card(s) remeshed | "
                    f"{errors} error(s)"
                )
            )

        else:

            self.report(
                {'INFO'},
                (
                    f"{len(results)} card(s) "
                    "remeshed successfully"
                )
            )


        return {'FINISHED'}


    # ============================================================
# TOOL
# MATCH UV ISLAND SIZE TO ACTIVE ISLAND
# ============================================================

class UV_OT_match_island_size(bpy.types.Operator):

    bl_idname = "uv.match_island_size"
    bl_label = "Match Island Size"
    bl_description = (
        "Resize selected UV islands to match "
        "the UV island containing the active face"
    )
    bl_options = {'REGISTER', 'UNDO'}


    def execute(self, context):

        obj = context.edit_object

        if obj is None or obj.type != 'MESH':

            self.report(
                {'WARNING'},
                "Select a mesh and enter Edit Mode"
            )

            return {'CANCELLED'}


        mesh = obj.data

        bm = bmesh.from_edit_mesh(
            mesh
        )

        uv_layer = (
            bm.loops.layers.uv.active
        )


        if uv_layer is None:

            self.report(
                {'WARNING'},
                "No active UV Map found"
            )

            return {'CANCELLED'}


        # ====================================================
        # ACTIVE FACE = REFERENCE
        # ====================================================

        active_face = bm.faces.active


        if (
            active_face is None
            or not active_face.select
        ):

            self.report(
                {'WARNING'},
                "Select an active reference face"
            )

            return {'CANCELLED'}


        # ====================================================
        # UV CONNECTION
        # ====================================================

        EPS = 1e-6


        def uv_close(a, b):

            return (
                a - b
            ).length < EPS


        def faces_uv_connected(
            face_a,
            face_b
        ):

            shared_edges = (
                set(face_a.edges)
                .intersection(
                    face_b.edges
                )
            )


            for edge in shared_edges:

                verts = list(
                    edge.verts
                )

                uv_a = {}
                uv_b = {}


                for loop in face_a.loops:

                    if loop.vert in verts:

                        uv_a[
                            loop.vert
                        ] = (
                            loop[
                                uv_layer
                            ].uv.copy()
                        )


                for loop in face_b.loops:

                    if loop.vert in verts:

                        uv_b[
                            loop.vert
                        ] = (
                            loop[
                                uv_layer
                            ].uv.copy()
                        )


                if (
                    len(uv_a) != 2
                    or len(uv_b) != 2
                ):
                    continue


                if all(
                    vert in uv_b
                    and uv_close(
                        uv_a[vert],
                        uv_b[vert]
                    )
                    for vert in uv_a
                ):

                    return True


            return False


        # ====================================================
        # GET UV ISLAND FROM A FACE
        # ====================================================

        def get_island(start_face, allowed_faces):

            allowed_set = set(
                allowed_faces
            )

            island = {
                start_face
            }

            stack = [
                start_face
            ]


            while stack:

                current = (
                    stack.pop()
                )


                for edge in current.edges:

                    for linked in edge.link_faces:

                        if (
                            linked not in allowed_set
                            or linked in island
                        ):
                            continue


                        if faces_uv_connected(
                            current,
                            linked
                        ):

                            island.add(
                                linked
                            )

                            stack.append(
                                linked
                            )


            return list(
                island
            )


        # ====================================================
        # SELECTED FACES
        # ====================================================

        selected_faces = [
            face
            for face in bm.faces
            if face.select
        ]


        if not selected_faces:

            self.report(
                {'WARNING'},
                "No faces selected"
            )

            return {'CANCELLED'}


        # ====================================================
        # DETECT SELECTED UV ISLANDS
        # ====================================================

        remaining = set(
            selected_faces
        )

        islands = []


        while remaining:

            start = next(
                iter(remaining)
            )

            island = get_island(
                start,
                remaining
            )


            for face in island:

                remaining.discard(
                    face
                )


            islands.append(
                island
            )


        # ====================================================
        # FIND REFERENCE ISLAND
        # ====================================================

        reference_island = None


        for island in islands:

            if active_face in island:

                reference_island = (
                    island
                )

                break


        if reference_island is None:

            self.report(
                {'WARNING'},
                "Could not find reference UV island"
            )

            return {'CANCELLED'}


        # ====================================================
        # BOUNDING BOX
        # ====================================================

        def get_bbox(island):

            uvs = []


            for face in island:

                for loop in face.loops:

                    uvs.append(
                        loop[
                            uv_layer
                        ].uv.copy()
                    )


            min_x = min(
                uv.x
                for uv in uvs
            )

            max_x = max(
                uv.x
                for uv in uvs
            )

            min_y = min(
                uv.y
                for uv in uvs
            )

            max_y = max(
                uv.y
                for uv in uvs
            )


            width = (
                max_x -
                min_x
            )

            height = (
                max_y -
                min_y
            )


            center = Vector((
                (
                    min_x +
                    max_x
                ) * 0.5,

                (
                    min_y +
                    max_y
                ) * 0.5
            ))


            return (
                center,
                width,
                height
            )


        # ====================================================
        # REFERENCE SIZE
        # ====================================================

        (
            reference_center,
            reference_width,
            reference_height
        ) = get_bbox(
            reference_island
        )


        if (
            reference_width <= 1e-10
            or reference_height <= 1e-10
        ):

            self.report(
                {'WARNING'},
                "Reference island has invalid dimensions"
            )

            return {'CANCELLED'}


        # ====================================================
        # RESIZE OTHER ISLANDS
        # ====================================================

        resized = 0


        for island in islands:

            # Do not modify the reference
            if island is reference_island:
                continue


            (
                center,
                width,
                height
            ) = get_bbox(
                island
            )


            if (
                width <= 1e-10
                or height <= 1e-10
            ):
                continue


            scale_x = (
                reference_width /
                width
            )

            scale_y = (
                reference_height /
                height
            )


            # ------------------------------------------------
            # SCALE AROUND ITS OWN CENTER
            # ------------------------------------------------

            for face in island:

                for loop in face.loops:

                    uv = (
                        loop[
                            uv_layer
                        ].uv
                    )


                    offset = (
                        uv -
                        center
                    )


                    offset.x *= (
                        scale_x
                    )

                    offset.y *= (
                        scale_y
                    )


                    uv.x = (
                        center.x +
                        offset.x
                    )

                    uv.y = (
                        center.y +
                        offset.y
                    )


            resized += 1


        # ====================================================
        # UPDATE
        # ====================================================

        bmesh.update_edit_mesh(
            mesh,
            loop_triangles=False,
            destructive=False
        )


        self.report(
            {'INFO'},
            f"{resized} island(s) matched to reference size"
        )


        return {'FINISHED'}


# ============================================================
# REGISTER
# ============================================================

classes = (
    UV_OT_select_quad_islands,

    UV_OT_straighten_hair_cards,
    UV_OT_force_straighten_hair_cards,

    UV_OT_align_islands_vertical,
    UV_OT_align_islands_horizontal,

    UV_OT_match_island_size,
    UV_OT_match_island_location,

    OBJECT_OT_qremesh_selected_cards,

    UV_PT_hair_cards_tools,
)


def register():

    for cls in classes:

        bpy.utils.register_class(
            cls
        )


def unregister():

    for cls in reversed(classes):

        bpy.utils.unregister_class(
            cls
        )


if __name__ == "__main__":
    register()