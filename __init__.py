# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

bl_info = {
    "name": "Surface Tools",
    "author": "X_Tu",
    "description": "Surface Tools",
    "blender": (3, 1, 0),
    "version": (0, 0, 2),
    "location": "View3D > Sidebar > Surface",
    "warning": "",
    "category": "Add Curve"
}
import bpy

from . import auto_load
from .i18n import langs

auto_load.init()


def register():
    bpy.app.translations.register(__name__, langs)
    auto_load.register()


def unregister():
    auto_load.unregister()
    bpy.app.translations.unregister(__name__)
