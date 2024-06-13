import mouette as M
import numpy as np
import cmath

import sys
import polyscope as ps
import polyscope.imgui as psim

# A bunch of parameters which we will manipulate via the UI defined below.
# There is nothing special about these variables, you could manipulate any other 
# kind of Python values the same way, such as entries in a dict, or class members.
cadFF : bool = True
align_features : bool = True
order : int = 4
cotans : bool = True
n_smooth : int = 3
alpha : float = 0.1
FF_elements = ["faces", "vertices"]
FF_element_selected = FF_elements[0]
surface_mesh = None

ps_surface = None
ps_singularities = None

barycenters = None

def compute_frame_field():
    global ps_surface, ps_singularities, surface_mesh, \
        cadFF, align_features, order, cotans, n_smooth, alpha, FF_elements, FF_element_selected, \
        barycenters
    
    print("OPTIONS:", {
        "element" : FF_element_selected,
        "order" : order,
        "cadFF" : cadFF,
        "features" : align_features,
        "n_smooth" : n_smooth,
        "alpha" : alpha,
    })

    ff = M.framefield.SurfaceFrameField(surface_mesh, FF_element_selected, 
        order, align_features, verbose=True, n_smooth=n_smooth, 
        smooth_attach_weight=alpha, use_cotan=cotans, cad_correction=cadFF)
    ### Smooth frame field
    ff.run()

    ### Export frame variables
    ff_var = np.array([cmath.rect(1., cmath.phase(x)/order) for x in ff.var])
    ff_var = np.stack([np.real(ff_var), np.imag(ff_var)], axis=-1)
    bX, bY = ff.conn._baseX.as_array(), ff.conn._baseY.as_array() # local bases
    ps_surface.add_tangent_vector_quantity("frames", ff_var, 
        bX, bY, n_sym=order, defined_on=FF_element_selected, 
        enabled=True,length=0.007, radius=0.0015)
    
    ### Export singularities
    if FF_element_selected == "vertices":
        if surface_mesh.faces.has_attribute("singuls"):
            surface_mesh.faces.delete_attribute("singuls") # clear data
        
        if not surface_mesh.faces.has_attribute("barycenter"):
            M.attributes.face_barycenter(surface_mesh)
            barycenters = surface_mesh.faces.get_attribute("barycenter").as_array(len(surface_mesh.faces))

        ff.flag_singularities()
        singus_indices = surface_mesh.faces.get_attribute("singuls").as_array(len(surface_mesh.faces))
        # ps_surface.add_scalar_quantity("singularities", singus_indices, defined_on="faces", enabled=True, datatype="symmetric", vminmax=(-1., 1.))
        singus_points = barycenters[singus_indices!=0]
        ps_singularities = ps.register_point_cloud("singularities", singus_points, enabled=True)
        ps_singularities.add_scalar_quantity("Indices", singus_indices[singus_indices != 0], datatype="symmetric", vminmax=(-1, 1), enabled=True)

    elif FF_element_selected == "faces":
        if surface_mesh.vertices.has_attribute("singuls"):
            surface_mesh.vertices.delete_attribute("singuls")
        ff.flag_singularities()
        singus_indices = surface_mesh.vertices.get_attribute("singuls").as_array(len(surface_mesh.vertices))
        # ps_surface.add_scalar_quantity("singularities", singus_indices, defined_on="vertices", enabled=True, datatype="symmetric", vminmax=(-1., 1.))
        singus_points = np.array(surface_mesh.vertices)[singus_indices!=0]
        ps_singularities = ps.register_point_cloud("singularities", singus_points, enabled=True)
        ps_singularities.add_scalar_quantity("Indices", singus_indices[singus_indices != 0], datatype="symmetric",vminmax=(-1,1), enabled=True)


def GUI_callback():
    global cadFF, align_features, order, cotans, n_smooth, alpha, FF_elements, FF_element_selected

    # == Settings

    # Use settings like this to change the UI appearance.
    # Note that it is a push/pop pair, with the matching pop() below.
    psim.PushItemWidth(150)

    # == Show text in the UI

    psim.TextUnformatted("Frame Field Computation")
    psim.Separator()

    # == Set parameters

    # Checkbox
    _, cadFF = psim.Checkbox("cadFF", cadFF) 
    psim.SameLine() 
    _, align_features = psim.Checkbox("Align with features edges", align_features) 
    psim.SameLine()
    _, cotans = psim.Checkbox("Cotan", cotans)

    _, order = psim.InputInt("order", order, step=1)

    _, n_smooth = psim.InputInt("smooth steps", n_smooth, step=1, step_fast=5) 

    # Input floats using two different styles of widget
    _, alpha = psim.InputFloat("smooth attach weight", alpha) 
    # psim.SameLine() 

    psim.PushItemWidth(200)
    changed = psim.BeginCombo("element", FF_element_selected)
    if changed:
        for val in FF_elements:
            _, selected = psim.Selectable(val, FF_element_selected==val)
            if selected:
                FF_element_selected = val
        psim.EndCombo()
    psim.PopItemWidth()

    if(psim.Button("RUN")): compute_frame_field()


if __name__ == "__main__":
    try:
        surface_mesh = M.mesh.load(sys.argv[1])
        surface_mesh = M.transform.fit_into_unit_cube(surface_mesh)
    except Exception as e:
        print(f"Could not load input mesh '{sys.argv[1]}'. Supported formats are .obj, .mesh, .off, .stl, .geogram_ascii")
        print("Exiting.")
        exit()

    ps.init()
    
    mesh_name = M.utils.get_filename(sys.argv[1])
    ps_surface = ps.register_surface_mesh(mesh_name, np.array(surface_mesh.vertices), np.array(surface_mesh.faces))

    ps.set_user_callback(GUI_callback)
    ps.show()