import adsk.core
import adsk.fusion


class FusionAdapter:
    def get_app_ui(self):
        app = adsk.core.Application.get()
        if not app:
            return None, None
        return app, app.userInterface

    def get_active_design(self):
        app, _ = self.get_app_ui()
        return adsk.fusion.Design.cast(app.activeProduct) if app else None

    def dims_mm(self, body):
        bbox = body.boundingBox
        min_pt = bbox.minPoint
        max_pt = bbox.maxPoint
        x_mm = abs(max_pt.x - min_pt.x) * 10.0
        y_mm = abs(max_pt.y - min_pt.y) * 10.0
        z_mm = abs(max_pt.z - min_pt.z) * 10.0
        dims = sorted([x_mm, y_mm, z_mm], reverse=True)
        return dims[0], dims[1], dims[2]

    def selected_bodies(self):
        _, ui = self.get_app_ui()
        if not ui:
            return []
        sels = ui.activeSelections
        if sels is None or sels.count == 0:
            return []
        out = []
        seen = set()
        for i in range(sels.count):
            ent = sels.item(i).entity
            body = adsk.fusion.BRepBody.cast(ent)
            if not body:
                face = adsk.fusion.BRepFace.cast(ent)
                if face:
                    body = face.body
            if not body:
                continue
            token = body.entityToken
            if token in seen:
                continue
            seen.add(token)
            out.append(("Selected", body))
        return out

    def selected_point_mm(self):
        _, ui = self.get_app_ui()
        if not ui:
            return None
        sels = ui.activeSelections
        if sels is None or sels.count == 0:
            return None

        for i in range(sels.count):
            ent = sels.item(i).entity
            sk_pt = adsk.fusion.SketchPoint.cast(ent)
            if sk_pt:
                g = sk_pt.geometry
                return [g.x * 10.0, g.y * 10.0, g.z * 10.0]

            vtx = adsk.fusion.BRepVertex.cast(ent)
            if vtx:
                g = vtx.geometry
                return [g.x * 10.0, g.y * 10.0, g.z * 10.0]

            cpt = adsk.fusion.ConstructionPoint.cast(ent)
            if cpt:
                g = cpt.geometry
                return [g.x * 10.0, g.y * 10.0, g.z * 10.0]

        return None

    def all_project_bodies(self, design):
        root = design.rootComponent
        if not root:
            return []

        out = []
        seen = set()
        for i in range(root.bRepBodies.count):
            body = root.bRepBodies.item(i)
            token = body.entityToken
            if token in seen:
                continue
            seen.add(token)
            out.append(("Root", body))

        for i in range(root.allOccurrences.count):
            occ = root.allOccurrences.item(i)
            comp = occ.component
            if not comp:
                continue
            for j in range(comp.bRepBodies.count):
                native_body = comp.bRepBodies.item(j)
                body = native_body.createForAssemblyContext(occ) if occ else native_body
                if not body:
                    continue
                token = body.entityToken
                if token in seen:
                    continue
                seen.add(token)
                out.append((occ.name, body))
        return out
