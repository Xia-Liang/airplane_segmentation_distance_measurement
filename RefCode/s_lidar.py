try:
    from config import *
    from manual_control import *
    from display import *
except ImportError:
    raise RuntimeError('cannot import config file')

try:
    from matplotlib import cm
    import open3d as o3d
    from datetime import datetime
except ImportError:
    raise RuntimeError('cannot import lidar necessary package')

surface = None

VIRIDIS = np.array(cm.get_cmap('plasma').colors)
VID_RANGE = np.linspace(0.0, 1.0, VIRIDIS.shape[0])
LABEL_COLORS = np.array([
    (255, 255, 255),  # None
    (70, 70, 70),  # Building
    (100, 40, 40),  # Fences
    (55, 90, 80),  # Other
    (220, 20, 60),  # Pedestrian
    (153, 153, 153),  # Pole
    (157, 234, 50),  # RoadLines
    (128, 64, 128),  # Road
    (244, 35, 232),  # Sidewalk
    (107, 142, 35),  # Vegetation
    (0, 0, 142),  # Vehicle
    (102, 102, 156),  # Wall
    (220, 220, 0),  # TrafficSign
    (70, 130, 180),  # Sky
    (81, 0, 81),  # Ground
    (150, 100, 100),  # Bridge
    (230, 150, 140),  # RailTrack
    (180, 165, 180),  # GuardRail
    (250, 170, 30),  # TrafficLight
    (110, 190, 160),  # Static
    (170, 120, 50),  # Dynamic
    (45, 60, 150),  # Water
    (145, 170, 100),  # Terrain
    (102, 0, 204),  # CPcut_Cockpit = 23u, dark purple
    (153, 51, 255),  # CPcut_Dome = 24u, light purple
    (0, 255, 0),  # CPcut_Empennage = 25u, green
    (255, 153, 51),  # CPcut_EngineLeft = 26u, dark orange
    (204, 102, 0),  # CPcut_EngineRight = 27u, light orange
    (153, 255, 204),  # CPcut_GearFront = 28u, light green
    (153, 255, 204),  # CPcut_GearLeft = 29u,
    (153, 255, 204),  # CPcut_GearRight = 30u,
    (255, 0, 0),  # CPcut_MainBody = 31u, red
    (204, 204, 0),  # CPcut_WingLeft = 32u, dark yellow
    (255, 255, 51)  # CPcut_WingRight = 33u, light yellow
]) / 255.0  # normalize each channel [0-1] since is what Open3D uses


# def process_img(image):
#     """
#     process the image
#     """
#     global surface
#     array = np.frombuffer(image.raw_data, dtype=np.dtype("uint8"))
#     array = np.reshape(array, (image.height, image.width, 4))
#     array = array[:, :, :3]
#     array = array[:, :, ::-1]  # switch r,g,b
#     array = array.swapaxes(0, 1)  # exchange the width and height
#     surface = pygame.surfarray.make_surface(array)  # Copy an array to a new surface
#
#     image_name = image.frame
#     image.save_to_disk('D:\\mb95541\\aeroplane\\image\\%d' % image_name)

def lidar_callback(point_cloud, point_list):
    """Prepares a point cloud with intensity colors ready to be consumed by Open3D"""
    data = np.copy(np.frombuffer(point_cloud.raw_data, dtype=np.dtype('f4')))
    data = np.reshape(data, (int(data.shape[0] / 4), 4))

    # Isolate the intensity and compute a color for it
    intensity = data[:, -1]
    intensity_col = 1.0 - np.log(intensity) / np.log(np.exp(-0.004 * 100))
    int_color = np.c_[
        np.interp(intensity_col, VID_RANGE, VIRIDIS[:, 0]),
        np.interp(intensity_col, VID_RANGE, VIRIDIS[:, 1]),
        np.interp(intensity_col, VID_RANGE, VIRIDIS[:, 2])]

    # Isolate the 3D data
    points = data[:, :-1]

    # We're negating the y to correclty visualize a world that matches
    # what we see in Unreal since Open3D uses a right-handed coordinate system
    points[:, :1] = -points[:, :1]

    # # An example of converting points from sensor to vehicle space if we had
    # # a carla.Transform variable named "tran":
    # points = np.append(points, np.ones((points.shape[0], 1)), axis=1)
    # points = np.dot(tran.get_matrix(), points.T).T
    # points = points[:, :-1]

    point_list.points = o3d.utility.Vector3dVector(points)
    point_list.colors = o3d.utility.Vector3dVector(int_color)


def semantic_lidar_callback(point_cloud, point_list):
    """Prepares a point cloud with semantic segmentation colors ready to be consumed by Open3D"""
    data = np.frombuffer(point_cloud.raw_data, dtype=np.dtype([
        ('x', np.float32), ('y', np.float32), ('z', np.float32),
        ('CosAngle', np.float32), ('ObjIdx', np.uint32), ('ObjTag', np.uint32)]))

    # We're negating the y to correclty visualize a world that matches
    # what we see in Unreal since Open3D uses a right-handed coordinate system
    points = np.array([data['x'], -data['y'], data['z']]).T

    # # An example of adding some noise to our data if needed:
    # points += np.random.uniform(-0.05, 0.05, size=points.shape)

    # Colorize the pointcloud based on the CityScapes color palette
    labels = np.array(data['ObjTag'])
    int_color = LABEL_COLORS[labels]

    # # In case you want to make the color intensity depending
    # # of the incident ray angle, you can use:
    # int_color *= np.array(data['CosAngle'])[:, None]

    point_list.points = o3d.utility.Vector3dVector(points)
    point_list.colors = o3d.utility.Vector3dVector(int_color)


def add_open3d_axis(vis):
    """Add a small 3D axis on Open3D Visualizer"""
    axis = o3d.geometry.LineSet()
    axis.points = o3d.utility.Vector3dVector(np.array([
        [0.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, 0.0, 1.0]]))
    axis.lines = o3d.utility.Vector2iVector(np.array([
        [0, 1],
        [0, 2],
        [0, 3]]))
    axis.colors = o3d.utility.Vector3dVector(np.array([
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, 0.0, 1.0]]))
    vis.add_geometry(axis)


def process_lidar(data):
    pass


def carla_main():
    # --- pygame show --- #
    # pygame.init()
    # display = pygame.display.set_mode((IMG_WIDTH, IMG_HEIGHT), pygame.HWSURFACE | pygame.DOUBLEBUF)
    # font = get_font()
    # clock = pygame.time.Clock()
    try:
        # --- client --- #
        client = carla.Client('localhost', 2000)
        client.set_timeout(10.0)  # connect with server

        # --- world --- #
        world = client.get_world()
        settings = world.get_settings()
        settings.synchronous_mode = False  # Disables synchronous mode
        world.apply_settings(settings)

        # --- weather --- #
        # change weather params: carla.WeatherParameters  https://carla.readthedocs.io/en/0.9.3/python_api_tutorial/
        # set_weather:  https://carla.readthedocs.io/en/0.9.3/python_api/#carlaweatherparameters
        # world.set_weather(carla.WeatherParameters.ClearNoon)

        # --- vehicle --- #
        blueprint_library = world.get_blueprint_library()
        vehicle_bp = blueprint_library.filter('model3')[0]
        # vehicle property  https://carla.readthedocs.io/en/0.9.3/python_api/#carlaactorblueprint
        vehicle_bp.set_attribute('role_name', 'runner')
        white = '255.0, 255.0, 255.0'
        vehicle_bp.set_attribute('color', white)

        # --- start point --- #
        # spawn point
        spawn_point = carla.Transform(carla.Location(x=280, y=315, z=3),
                                      carla.Rotation(pitch=0.000000, yaw=270.000, roll=0.000000))
        print('spawn_point:', spawn_point)
        # generate the vehicle
        vehicle = world.spawn_actor(vehicle_bp, spawn_point)
        print("vehicle is spawned!")
        # set the physics Determines whether an actor will be affected by physics or not
        vehicle.set_simulate_physics(True)
        actor_list.append(vehicle)

        # --- lidar sensor --- #
        lidar_bp = blueprint_library.find('sensor.lidar.ray_cast_semantic')
        lidar_bp.set_attribute("channels", "16")  # Number of lasers.
        lidar_bp.set_attribute("range", "100.0")  # Maximum distance to measure/raycast in meters
        lidar_bp.set_attribute("points_per_second", "36000")  # Points generated by all lasers per second. default 56000
        lidar_bp.set_attribute("rotation_frequency", "10")  # Lidar rotation frequency. default 10
        lidar_bp.set_attribute("upper_fov", "25")  # Angle in degrees of the highest laser.
        lidar_bp.set_attribute("lower_fov", "-25")  # Angle in degrees of the lowest laser.
        lidar_bp.set_attribute("sensor_tick", "0.0")  # Simulation seconds between sensor captures (ticks).

        # add sensor to the vehicle, put the sensor in the car. rotation y x z
        spawn_point = carla.Transform(carla.Location(x=0.5, y=0.0, z=3),
                                      carla.Rotation(pitch=0.0, yaw=0.0, roll=0.0))
        lidar = world.spawn_actor(lidar_bp, spawn_point, attach_to=vehicle)
        actor_list.append(lidar)
        # open3d setup
        point_list = o3d.geometry.PointCloud()
        lidar.listen(lambda data: semantic_lidar_callback(data, point_list))

        # open3d vis
        vis = o3d.visualization.Visualizer()
        vis.create_window(
            window_name='Carla Lidar',
            width=960,
            height=540,
            left=480,
            top=270)
        vis.get_render_option().background_color = [0.05, 0.05, 0.05]
        vis.get_render_option().point_size = 1
        vis.get_render_option().show_coordinate_frame = True
        vis.add_geometry(point_list)

        frame = 0
        dt0 = datetime.now()

        # controller = KeyboardControl(vehicle)
        while True:
            # if should_quit():
            #     return
            # clock.tick(30)

            # don't delete! Will crash if surface is None
            if not surface:
                continue

            #  open3d display
            vis.update_geometry(point_list)
            vis.poll_events()
            vis.update_renderer()
            # # This can fix Open3D jittering issues:
            time.sleep(0.005)
            dt0 = datetime.now()
            frame += 1

            # # pygame display
            # controller.parse_events(clock)
            # vehicle_velocity = get_speed(vehicle)
            # # print(vehicle_velocity)
            # display.blit(font.render('% 5d FPS (real)' % clock.get_fps(), True, (255, 255, 255)), (8, 10))
            # display.blit(font.render('% 5d mk/h (velocity)' % vehicle_velocity, True, (0, 0, 0)), (8, 46))
            # pygame.display.flip()
            # display.blit(surface, (0, 0))

    finally:
        print('destroying actors')
        for actor in actor_list:
            actor.destroy()
        # pygame.quit()
        vis.destroy_window()
        print('done.')


if __name__ == '__main__':
    carla_main()
