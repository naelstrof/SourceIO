from pprint import pformat
from typing import Any

import bpy

from SourceIO.blender_bindings.material_loader.shader_base import Nodes, ExtraMaterialParameters
from SourceIO.blender_bindings.material_loader.shaders.source2_shader_base import Source2ShaderBase
from SourceIO.blender_bindings.utils.bpy_utils import is_blender_4_3
from SourceIO.library.source2.blocks.kv3_block import KVBlock


class CSGOEnvironmentBlend(Source2ShaderBase):
    SHADER: str = 'csgo_environment_blend.vfx'

    def create_nodes(self, material: bpy.types.Material, extra_parameters: dict[ExtraMaterialParameters, Any]):
        if super().create_nodes(material, extra_parameters) in ['UNKNOWN', 'LOADED']:
            return
        material_output = self.create_node(Nodes.ShaderNodeOutputMaterial)
        shader = self.create_node_group("csgo_lightmappedgeneric.vfx", name=self.SHADER)
        self.connect_nodes(shader.outputs['BSDF'], material_output.inputs['Surface'])
        material_data = self._material_resource
        data = self._material_resource.get_block(KVBlock, block_name='DATA')
        self.logger.info(pformat(dict(data)))

        vcolor_node = self.create_node(Nodes.ShaderNodeVertexColor)
        vcolor_node.layer_name = "COLOR"
        self.connect_nodes(vcolor_node.outputs[0], shader.inputs["BlendModulate"])

        if self._have_texture("g_tColor1"):
            color0_texture = self._get_texture("g_tColor1", (1, 1, 1, 1))
            self.connect_nodes(color0_texture.outputs[0], shader.inputs["TextureColor0"])
            if (material_data.get_int_property("F_ALPHA_TEST", 0) or
                    material_data.get_int_property("S_TRANSLUCENT", 0)):
                self.connect_nodes(color0_texture.outputs[1], shader.inputs["TextureAlpha0"])

        if self._have_texture("g_tColor2"):
            color_texture = self._get_texture("g_tColor2", (1, 1, 1, 1))
            if (material_data.get_int_property("F_ALPHA_TEST", 0) or
                    material_data.get_int_property("S_TRANSLUCENT", 0)):
                self.connect_nodes(color_texture.outputs[1], shader.inputs["TextureAlpha1"])

            self.connect_nodes(color_texture.outputs[0], shader.inputs["TextureColor1"])

        if self._have_texture("g_tNormal1"):
            normal0_texture = self._get_texture("g_tNormal1", (0.5, 0.5, 1, 1), True)
            self.connect_nodes(normal0_texture.outputs[0], shader.inputs["TextureNormal0"])
            self.connect_nodes(normal0_texture.outputs[1], shader.inputs["TextureRoughness0"])

        if self._have_texture("g_tNormal2"):
            normal_texture = self._get_texture("g_tNormal2", (0.5, 0.5, 1, 1), True)
            self.connect_nodes(normal_texture.outputs[0], shader.inputs["TextureNormal1"])
            self.connect_nodes(normal_texture.outputs[1], shader.inputs["TextureRoughness1"])

        if self._have_texture("g_tHeight1"):
            color_texture = self._get_texture("g_tHeight1", (1, 1, 1, 1), True)
            split = self.create_node(Nodes.ShaderNodeSeparateRGB)
            self.connect_nodes(color_texture.outputs[0], split.inputs[0])
            self.connect_nodes(split.outputs[0], shader.inputs["V0"])

        if self._have_texture("g_tHeight2"):
            color_texture = self._get_texture("g_tHeight2", (1, 1, 1, 1), True)
            split = self.create_node(Nodes.ShaderNodeSeparateRGB)
            self.connect_nodes(color_texture.outputs[0], split.inputs[0])
            self.connect_nodes(split.outputs[0], shader.inputs["V1"])

        if self._have_texture("g_tSharedColorOverlay"):
            scale = material_data.get_vector_property("g_vOverlayTexCoordScale", None)

            detail_texture = self._get_texture("g_tSharedColorOverlay", (1, 1, 1, 1))
            if scale is not None:
                uv_node = self.create_node(Nodes.ShaderNodeUVMap)
                uv_node.uv_map = "TEXCOORD"
                uv_transform = self.create_node_group("UVTransform")
                if scale is not None:
                    uv_transform.inputs["g_vTexCoordScale"].default_value = scale[:3]

                self.connect_nodes(uv_node.outputs[0], uv_transform.inputs[0])

                self.connect_nodes(uv_transform.outputs[0], detail_texture.inputs[0])

            self.connect_nodes(detail_texture.outputs[0], shader.inputs["TextureDetail0"])
            self.connect_nodes(detail_texture.outputs[0], shader.inputs["TextureDetail1"])
            shader.inputs["F_DETAIL_TEXTURE"].default_value = 2.0
            shader.inputs["g_flDetailBlendFactor"].default_value = 2

        if ExtraMaterialParameters.USE_OBJECT_TINT in extra_parameters:
            object_color = self.create_node(Nodes.ShaderNodeObjectInfo)
            self.connect_nodes(object_color.outputs["Color"], shader.inputs["ModelTint"])

        shader.inputs["Softness"].default_value = material_data.get_float_property("g_flBlendSoftness", 0.5)
        shader.inputs["Sharpness"].default_value = material_data.get_float_property("g_flBevelBlendSharpness", 4)

        if material_data.get_int_property("F_ALPHA_TEST", 0):
            if not is_blender_4_3():
                self.bpy_material.blend_method = 'CLIP'
                self.bpy_material.shadow_method = 'CLIP'
                self.bpy_material.alpha_threshold = material_data.get_float_property("g_flAlphaTestReference", 0.5)
        elif material_data.get_int_property("S_TRANSLUCENT", 0):
            if not is_blender_4_3():
                self.bpy_material.blend_method = 'HASHED'
                self.bpy_material.shadow_method = 'CLIP'
        elif material_data.get_int_property("F_OVERLAY", 0):
            if not is_blender_4_3():
                self.bpy_material.blend_method = 'HASHED'
                self.bpy_material.shadow_method = 'CLIP'
