"""Server route routers."""

from mechatronics3.server.routes.detection import router as detection_router
from mechatronics3.server.routes.files import router as files_router
from mechatronics3.server.routes.robot import router as robot_router

__all__ = ["detection_router", "files_router", "robot_router"]
