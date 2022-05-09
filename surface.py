import logging
from typing import List, Optional, Tuple

import bpy
from bpy import context as Context
from bpy.types import Object, Operator, Panel
from bpy_extras import object_utils
from mathutils import Matrix, Vector

from .constants import CATEGORY_NAME

logger = logging.getLogger(__name__)


class SURFACE_PT_Generate_Surface(Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = CATEGORY_NAME
    bl_label = "Generate Surface"

    # bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        col = self.layout.column(align=True)
        col.operator(SURFACE_OT_Sweep1.bl_idname)
        col.operator(SURFACE_OT_Sweep2.bl_idname)


class SURFACE_OT_Sweep1(Operator):
    bl_idname = "surface_tools.sweep1"
    bl_label = "Sweep1"
    bl_options = {'REGISTER', 'UNDO'}

    cutting_object: Object = None
    track_object: Object = None
    cutting_is_reverse: bool = None
    track_is_reverse: bool = None

    @classmethod
    def poll(cls, context: Context):
        if len(context.selected_objects) != 2:
            return False
        cls.cutting_object = context.active_object
        selected_objects = context.selected_objects
        selected_objects.remove(cls.cutting_object)
        cls.track_object = selected_objects[0]
        if not_nurbs_objects(cls.cutting_object, cls.track_object):
            return False
        check_result = check_reverse(cls.cutting_object, cls.track_object)
        if check_result is None:
            return False
        cls.cutting_is_reverse, cls.track_is_reverse = check_result
        return True

    def execute(self, context: Context):
        cutting_object = self.cutting_object
        track_object = self.track_object

        # 创建一个新的表面
        surface_data = bpy.data.curves.new('Surface', type='SURFACE')
        surface_object = object_utils.object_data_add(context, surface_data)
        # surface_data.dimensions = '3D'
        surface_object.matrix_world = cutting_object.matrix_world
        surface_object.rotation_euler = cutting_object.rotation_euler
        # surface_object.show_wire = True
        # surface_object.show_in_front = True

        transform = cutting_object.matrix_world.inverted() @ track_object.matrix_world
        cutting_points = cutting_object.data.splines[0].points
        track_points = track_object.data.splines[0].points
        len_cutting = len(cutting_points)
        len_track = len(track_points)
        # 检查cutting_points的顺序
        if self.cutting_is_reverse:
            cutting_points = cutting_points.values()[::-1]
        # 检查track_points的顺序
        if self.track_is_reverse:
            track_points = track_points.values()[::-1]

        # 生成第一条样条线
        spline1 = surface_data.splines.new(type='NURBS')
        spline1.use_endpoint_u = True
        spline1.use_endpoint_v = True
        spline1.points.add(len_cutting - 1)
        for i in range(len_cutting):
            spline1.points[i].co = cutting_points[i].co
            # 选择所有顶点用于后续制作曲面
            spline1.points[i].select = True

        bpy.ops.object.mode_set(mode='EDIT')
        A = Vector(cutting_points[0].co[:3])
        B = Vector(cutting_points[-1].co[:3])
        # 生成后续样条线
        for i in range(1, len_track):
            spline = surface_data.splines.new(type='NURBS')
            spline.use_endpoint_u = True
            spline.use_endpoint_v = True
            spline.points.add(len_cutting - 1)
            spline.points[0].co = transform @ track_points[i].co
            # 选择所有顶点用于后续制作曲面
            spline.points[0].select = True
            D = Vector((transform @ track_points[i].co)[:3])
            E = D + B - A
            for j in range(1, len_cutting):
                C = Vector(cutting_points[j].co[:3])
                ex = B - A
                ey = D - A
                ez = ex.cross(ey)
                mat1 = Matrix((ex, ey, ez))
                mat1.transpose()
                mat1.invert()
                ex2 = E - D
                scale = ex2.length / ex.length
                ey2 = scale * ey
                ez2 = scale * ez.length * ex2.cross(ey2).normalized()
                mat2 = Matrix((ex2, ey2, ez2))
                mat2.transpose()
                F = D + mat2 @ mat1 @ (C - A)
                spline.points[j].co = (*F, 1)
                # 选择所有顶点用于后续制作曲面
                spline.points[j].select = True
            # bpy.ops.curve.make_segment()

        for spline in surface_data.splines:
            # spline.resolution_u = 4
            # spline.resolution_v = 4
            spline.order_u = len_track
            spline.order_v = len_cutting
            # for p in spline.points:
            #     p.select = False

        # bpy.ops.object.mode_set(mode='OBJECT')

        return {'FINISHED'}


class SURFACE_OT_Sweep2(Operator):
    bl_idname = "surface_tools.sweep2"
    bl_label = "Sweep2"
    bl_options = {'REGISTER', 'UNDO'}

    cutting_object: Object = None
    track1_object: Object = None
    track2_object: Object = None
    cutting_is_reverse: bool = None
    track1_is_reverse: bool = None
    track2_is_reverse: bool = None

    @classmethod
    def poll(cls, context):
        if len(context.selected_objects) != 3:
            return False
        if not_nurbs_objects(*context.selected_objects):
            return False
        cls.cutting_object = context.active_object
        selected_objects = context.selected_objects
        selected_objects.remove(cls.cutting_object)
        cls.track1_object, cls.track2_object = selected_objects
        # TODO 现在假设两个轨道物体都只有一条样条线
        if len(cls.track1_object.data.splines[0].points) != len(
                cls.track2_object.data.splines[0].points):
            # 此种情况为两条轨道的控制点数量不一致
            return False
        check_result = check_reverse(cls.cutting_object, cls.track1_object)
        if check_result is None:
            return False
        cls.cutting_is_reverse, cls.track1_is_reverse = check_result
        check_result = check_reverse(cls.cutting_object, cls.track2_object)
        if check_result is None:
            return False
        cutting_is_reverse, cls.track2_is_reverse = check_result
        if cls.cutting_is_reverse == cutting_is_reverse:
            # 此种情况为两条轨道都接在了截线的同一个端点上
            return False
        return True

    def execute(self, context):
        cutting_object = self.cutting_object
        track1_object = self.track1_object
        track2_object = self.track2_object

        # 创建一个新的表面
        surface_data = bpy.data.curves.new('Surface', type='SURFACE')
        surface_object = object_utils.object_data_add(context, surface_data)
        # surface_data.dimensions = '3D'
        surface_object.matrix_world = cutting_object.matrix_world
        surface_object.rotation_euler = cutting_object.rotation_euler
        # surface_object.show_wire = True
        # surface_object.show_in_front = True

        cutting_matrix = cutting_object.matrix_world.inverted()
        transform1 = cutting_matrix @ track1_object.matrix_world
        transform2 = cutting_matrix @ track2_object.matrix_world
        cutting_points = cutting_object.data.splines[0].points
        track1_points = track1_object.data.splines[0].points
        track2_points = track2_object.data.splines[0].points
        len_cutting = len(cutting_points)
        len_track = len(track1_points)  # TODO 假设两条轨道的控制点数量一致
        # 检查cutting_points的顺序
        if self.cutting_is_reverse:
            cutting_points = cutting_points.values()[::-1]
        # 检查track1_points的顺序
        if self.track1_is_reverse:
            track1_points = track1_points.values()[::-1]
        # 检查track2_points的顺序
        if self.track2_is_reverse:
            track2_points = track2_points.values()[::-1]

        # 生成第一条样条线
        spline1 = surface_data.splines.new(type='NURBS')
        spline1.use_endpoint_u = True
        spline1.use_endpoint_v = True
        spline1.points.add(len_cutting - 1)
        for i in range(len_cutting):
            spline1.points[i].co = cutting_points[i].co
            # 选择所有顶点用于后续制作曲面
            spline1.points[i].select = True

        bpy.ops.object.mode_set(mode='EDIT')
        A = Vector(cutting_points[0].co[:3])
        B = Vector(cutting_points[-1].co[:3])
        # 生成后续样条线
        for i in range(1, len_track):
            spline = surface_data.splines.new(type='NURBS')
            spline.use_endpoint_u = True
            spline.use_endpoint_v = True
            spline.points.add(len_cutting - 1)
            spline.points[0].co = transform1 @ track1_points[i].co
            spline.points[-1].co = transform2 @ track2_points[i].co
            # 选择所有顶点用于后续制作曲面
            spline.points[0].select = True
            spline.points[-1].select = True
            D = Vector((transform1 @ track1_points[i].co)[:3])
            E = Vector((transform2 @ track2_points[i].co)[:3])
            for j in range(1, len_cutting - 1):
                C = Vector(cutting_points[j].co[:3])
                ex = B - A
                ey = D - A
                ez = ex.cross(ey)
                mat1 = Matrix((ex, ey, ez))
                mat1.transpose()
                mat1.invert()
                ex2 = E - D
                scale = ex2.length / ex.length
                ey2 = scale * ey
                ez2 = scale * ez.length * ex2.cross(ey2).normalized()
                mat2 = Matrix((ex2, ey2, ez2))
                mat2.transpose()
                F = D + mat2 @ mat1 @ (C - A)
                spline.points[j].co = (*F, 1)
                # 选择所有顶点用于后续制作曲面
                spline.points[j].select = True
            bpy.ops.curve.make_segment()

        for spline in surface_data.splines:
            # spline.resolution_u = 4
            # spline.resolution_v = 4
            spline.order_u = len_track
            spline.order_v = len_cutting
            for p in spline.points:
                p.select = False

        bpy.ops.object.mode_set(mode='OBJECT')

        return {'FINISHED'}


def not_nurbs_object(object: Object) -> bool:
    not_nurbs = lambda spline: spline.type != 'NURBS'
    return object.type != 'CURVE' or any(map(not_nurbs, object.data.splines))


def not_nurbs_objects(*objects: List[Object]) -> bool:
    return any(map(not_nurbs_object, objects))


def check_reverse(first_object: Object,
                  second_object: Object) -> Optional[Tuple[bool, bool]]:
    '''
    检查两条线是否相接，以及点集顺序是否需要反转
    注意: 两个物体必须为NURBS曲线
    '''
    first_point = first_object.matrix_world @ first_object.data.splines[
        0].points[0].co
    second_point = first_object.matrix_world @ first_object.data.splines[
        0].points[-1].co
    third_point = second_object.matrix_world @ second_object.data.splines[
        0].points[0].co
    fourth_point = second_object.matrix_world @ second_object.data.splines[
        0].points[-1].co
    if (first_point - third_point).length <= 1e-04:
        return (False, False)
    if (first_point - fourth_point).length <= 1e-04:
        return (False, True)
    if (second_point - third_point).length <= 1e-04:
        return (True, False)
    if (second_point - fourth_point).length <= 1e-04:
        return (True, True)
