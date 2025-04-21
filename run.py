import mouette as M
import numpy as np
import cmath

import sys
import os
import polyscope as ps
import polyscope.imgui as psim

#### Parameters for smooth FF
cadFF : bool = True
align_features : bool = False
order : int = 4
cotans : bool = True
n_smooth : int = 3
alpha : float = 1.
FF_element_selected = "vertices"

#### Parameters for curvature FF
curv_align_features : bool = False
confidence_threshold : float = 0.5
smooth_threshold : float = 0.7
curv_n_smooth : int = 3
patch_size : int = 2
curv_alpha : float = 1.
curv_element_selected = "vertices"

#### Global variables
surface_mesh = None
ps_surface = None
ps_singularities = None
face_barycenters = None
FF = None
FFtype = (None, None)


BLACK = [0., 0., 0.]


def export_as_geogram_ascii():
    global FF, surface_mesh
    mesh_name = M.utils.get_filename(sys.argv[1])
    os.makedirs("output", exist_ok=True)
    M.mesh.save(surface_mesh, f"output/{mesh_name}.geogram_ascii")
    M.mesh.save(FF.export_as_mesh(), f"output/{mesh_name}_FF.geogram_ascii")

def compute_frame_field():
    # Parameters from global values
    global cadFF, align_features, order, cotans, n_smooth, alpha, FF_element_selected

    # Global variables
    global FF, ps_surface, ps_singularities, surface_mesh, face_barycenters, FFtype
    FFtype = "smooth"
    
    print("OPTIONS:", {
        "element" : FF_element_selected,
        "order" : order,
        "cadFF" : cadFF,
        "features" : align_features,
        "n_smooth" : n_smooth,
        "alpha" : alpha,
    })

    # Clear window
    ps_surface.remove_all_quantities()
    ps.remove_curve_network("ff_edges", error_if_absent=False)
    ps.remove_point_cloud("singularities", error_if_absent=False)
    
    ### Build the frame field
    FF = M.framefield.SurfaceFrameField(surface_mesh, FF_element_selected, 
        order, align_features, verbose=True, n_smooth=n_smooth, 
        smooth_attach_weight=alpha, use_cotan=cotans, cad_correction=cadFF)
    FF.run()

    ### Export frame variables
    ff_var = np.array([cmath.rect(1., cmath.phase(x)/order) for x in FF.var])
    ff_var = np.stack([np.real(ff_var), np.imag(ff_var)], axis=-1)
    bX, bY = FF.conn.bX, FF.conn.bY # local bases
    
    if FF_element_selected == "edges":
        ff_mesh = FF.export_as_mesh(length_mult=1.3)
        ps.register_curve_network("ff_edges", np.asarray(ff_mesh.vertices), np.asarray(ff_mesh.edges), radius=0.0002, color=BLACK, material="flat")
    else:
        ps_surface.add_tangent_vector_quantity("frames", ff_var, 
            bX, bY, n_sym=order, defined_on=FF_element_selected, 
            enabled=True, length=0.005, radius=0.0005, color=BLACK)            

def compute_curvature_frame_field():
    global curv_align_features, confidence_threshold, smooth_threshold, curv_n_smooth, patch_size, curv_alpha, curv_element_selected 
    
    global FF, ps_surface, ps_singularities, surface_mesh, face_barycenters, FFtype
    FFtype = "curvature"

    print("OPTIONS:", {
        "element" : curv_element_selected,
        "features" : curv_align_features,
        "n_smooth" : curv_n_smooth,
        "alpha" : curv_alpha,
        "confidence_threshold" : confidence_threshold,
        "smooth_threshold" : smooth_threshold,
        "patch_size" : patch_size,
    })
    # Clear window
    ps_surface.remove_all_quantities()
    ps.remove_curve_network("ff_edges", error_if_absent=False)
    ps.remove_point_cloud("singularities", error_if_absent=False)

    FF = M.framefield.PrincipalDirections(surface_mesh, curv_element_selected, 
        align_features, verbose=True, n_smooth=n_smooth, patch_size=patch_size,
        confidence_threshold=confidence_threshold, smooth_threshold=smooth_threshold,
        smooth_attach_weight=alpha)
    FF.run()
     ### Export frame variables
    ff_var = np.array([cmath.rect(1., cmath.phase(x)/order) for x in FF.var])
    ff_var = np.stack([np.real(ff_var), np.imag(ff_var)], axis=-1)
    bX, bY = FF.conn.bX, FF.conn.bY # local bases
    ps_surface.add_tangent_vector_quantity("frames", ff_var, 
            bX, bY, n_sym=order, defined_on=curv_element_selected, 
            enabled=True, length=0.005, radius=0.0005, color=BLACK)


def flag_singularities():
    # Parameters from global values
    global FF_element_selected, curv_element_selected
    global FF, ps_surface, ps_singularities, surface_mesh, face_barycenters, FFtype

    if FF is None:
        ps.error("No frame field is computed. Click run before attempting to find singularities.")

    if (FFtype, FF_element_selected) == ("smooth", "vertices") or (FFtype, curv_element_selected) == ("curvature", "vertices"):
        if surface_mesh.faces.has_attribute("singuls"):
            surface_mesh.faces.delete_attribute("singuls") # clear data
        FF.flag_singularities()
        singus_indices = surface_mesh.faces.get_attribute("singuls").as_array(len(surface_mesh.faces))
        singus_points = face_barycenters[singus_indices!=0]
        ps_singularities = ps.register_point_cloud("singularities", singus_points, radius=0.003, enabled=True)
        ps_singularities.add_scalar_quantity("Indices", singus_indices[singus_indices != 0], datatype="symmetric", vminmax=(-1, 1), enabled=True)

    elif (FFtype, FF_element_selected) == ("smooth", "faces") or (FFtype, curv_element_selected) == ("curvature", "faces"):
        if surface_mesh.vertices.has_attribute("singuls"):
            surface_mesh.vertices.delete_attribute("singuls")
        FF.flag_singularities()
        singus_indices = surface_mesh.vertices.get_attribute("singuls").as_array(len(surface_mesh.vertices))
        singus_points = np.array(surface_mesh.vertices)[singus_indices!=0]
        ps_singularities = ps.register_point_cloud("singularities", singus_points, radius=0.003, enabled=True)
        ps_singularities.add_scalar_quantity("Indices", singus_indices[singus_indices != 0], datatype="symmetric",vminmax=(-1,1), enabled=True)        

    elif FFtype=="smooth" and FF_element_selected == "edges":
        # there may be singularities both inside faces and at vertices
        if surface_mesh.vertices.has_attribute("singuls"):
            surface_mesh.vertices.delete_attribute("singuls")
        if surface_mesh.faces.has_attribute("singuls"):
            surface_mesh.faces.delete_attribute("singuls") # clear data
        FF.flag_singularities()
        singus_indicesV = surface_mesh.vertices.get_attribute("singuls").as_array(len(surface_mesh.vertices))
        singus_pointsV = np.array(surface_mesh.vertices)[singus_indicesV!=0]
        singus_indicesF = surface_mesh.faces.get_attribute("singuls").as_array(len(surface_mesh.faces))
        singus_pointsF = face_barycenters[singus_indicesF!=0]

        singus_points = np.concatenate((singus_pointsV, singus_pointsF))
        singus_indices = np.concatenate((singus_indicesV[singus_indicesV != 0], singus_indicesF[singus_indicesF != 0]))
        ps_singularities = ps.register_point_cloud("singularities", singus_points, radius=0.003, enabled=True)
        ps_singularities.add_scalar_quantity("Indices", singus_indices[singus_indices != 0], datatype="symmetric",vminmax=(-1,1), enabled=True)



def GUI_callback():
    global cadFF, align_features, order, cotans, n_smooth, alpha, FF_element_selected
    global curv_align_features, confidence_threshold, smooth_threshold, curv_n_smooth, patch_size, curv_alpha, curv_element_selected

    ### Smooth Frame Field Options
    psim.PushItemWidth(150)

    psim.TextUnformatted("     Smooth Frame Field")
    psim.Separator()
    _, cadFF = psim.Checkbox("cadFF", cadFF) 
    psim.SameLine() 
    _, align_features = psim.Checkbox("Align with features edges", align_features) 
    psim.SameLine()
    _, cotans = psim.Checkbox("Cotan", cotans)
    _, order = psim.InputInt("order", order, step=1)
    _, n_smooth = psim.InputInt("Smooth steps", n_smooth, step=1, step_fast=5) 

    _, alpha = psim.InputFloat("smooth attach weight", alpha) 

    psim.PushItemWidth(200)
    changed = psim.BeginCombo("Defined on", FF_element_selected)
    if changed:
        for val in ["faces", "vertices", "edges"]:
            _, selected = psim.Selectable(val, FF_element_selected==val)
            if selected:
                FF_element_selected = val
        psim.EndCombo()
    psim.PopItemWidth()

    if psim.Button("Run") : compute_frame_field()
    psim.SameLine()
    if psim.Button("Find singularities") : flag_singularities()
    psim.NewLine()

    #### Principal Directions of Curvature options
    psim.TextUnformatted("      Principal Directions of Curvature")
    psim.Separator()
    _, curv_align_features = psim.Checkbox("Align with features edges ", curv_align_features)
    _, patch_size = psim.InputInt("Patch size", patch_size, step=1, step_fast=1)
    _, confidence_threshold = psim.InputFloat("Confidence threshold", confidence_threshold) 
    
    _, curv_n_smooth = psim.InputInt("Smooth steps ", curv_n_smooth, step=1, step_fast=1)
    _, smooth_threshold = psim.InputFloat("Smooth threshold", smooth_threshold)
    _, curv_alpha = psim.InputFloat("Smooth attach weight", curv_alpha) 

    confidence_threshold = max(min(confidence_threshold, 1.), 0.)
    smooth_threshold = max(min(smooth_threshold, 1.), 0.) 

    psim.PushItemWidth(200)
    changed = psim.BeginCombo("Defined on ", curv_element_selected)
    if changed:
        for val in ["faces", "vertices"]:
            _, selected = psim.Selectable(val, curv_element_selected==val)
            if selected:
                curv_element_selected = val
        psim.EndCombo()
    psim.PopItemWidth()
    if(psim.Button("Run ")): compute_curvature_frame_field()
    psim.SameLine()
    if psim.Button("Find singularities ") : flag_singularities()
    psim.NewLine()


    #### Output button
    psim.Separator()
    if(psim.Button("EXPORT RESULT (.geogram_ascii)")): export_as_geogram_ascii()


if __name__ == "__main__":
    try:
        surface_mesh = M.mesh.load(sys.argv[1])
        surface_mesh = M.transform.fit_into_unit_cube(surface_mesh)
    except Exception as e:
        print(f"Could not load input mesh '{sys.argv[1]}'. Supported formats are .obj, .mesh, .off, .stl, .geogram_ascii")
        print("Exiting.")
        exit()

    ps.init()
    ps.set_ground_plane_mode("none")
    ps.set_display_message_popups(True)
    
    mesh_name = M.utils.get_filename(sys.argv[1])
    ps_surface = ps.register_surface_mesh(mesh_name, np.array(surface_mesh.vertices), np.array(surface_mesh.faces))
    face_barycenters = M.attributes.face_barycenter(surface_mesh, persistent=False).as_array(len(surface_mesh.faces))

    ps.set_user_callback(GUI_callback)
    ps.show()