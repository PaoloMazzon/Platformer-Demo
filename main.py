from math import ceil, cos, floor, sin
import pykraken as kn
import xml.etree.ElementTree as ET
from random import uniform as rand

# Tool to do collisions with grids in O(1) time. Collisions with TileMap work by
# checking the four corners on a hitbox and seeing if any of those four corners
# are inside an occupied cell in the tilemap. This type of collision only works
# when the hitbox is smaller or equal size to a cell in the tilemap.
class TileMap:
    def __init__(self, width: int, height: int, cell_width: float, cell_height: float):
        self.width = width
        self.height = height
        self.cell_width = cell_width
        self.cell_height = cell_height
        self.tiles = [0 for x in range(width * height)]
    
    def set(self, x: int, y: int, val: int):
        if x < 0 or x >= self.width or y < 0 or y >= self.height: return
        self.tiles[(y * self.width) + x] = val
    
    def get(self, x: int, y: int) -> int:
        if x < 0 or x >= self.width or y < 0 or y >= self.height: return 1
        return self.tiles[(y * self.width) + x]
    
    # Returns true if the hitbox is overlapping with any non-zero tile. Hitbox is relative to x/y
    def colliding(self, x: float, y: float, hitbox: kn.Rect) -> bool:
        x1 = floor((hitbox.x + x) / self.cell_width)
        y1 = floor((hitbox.y + y) / self.cell_height)
        x2 = floor(((hitbox.x + x) + hitbox.w) / self.cell_width)
        y2 = floor(((hitbox.y + y) + hitbox.h) / self.cell_height)
        return (
            self.get(x1, y1) != 0 or
            self.get(x2, y1) != 0 or
            self.get(x1, y2) != 0 or
            self.get(x2, y2) != 0
        )
    
    # Returns either a rectangle specifying the tile the hitbox is colliding with or None if no collision
    def colliding_with(self, x: float, y: float, hitbox: kn.Rect) -> kn.Rect | None:
        x1 = floor((hitbox.x + x) / self.cell_width)
        y1 = floor((hitbox.y + y) / self.cell_height)
        x2 = floor(((hitbox.x + x) + hitbox.w) / self.cell_width)
        y2 = floor(((hitbox.y + y) + hitbox.h) / self.cell_height)
        if self.get(x1, y1): return kn.Rect(x1 * self.cell_width, y1 * self.cell_height, self.cell_width, self.cell_height)
        if self.get(x2, y1): return kn.Rect(x2 * self.cell_width, y1 * self.cell_height, self.cell_width, self.cell_height)
        if self.get(x1, y2): return kn.Rect(x1 * self.cell_width, y2 * self.cell_height, self.cell_width, self.cell_height)
        if self.get(x2, y2): return kn.Rect(x2 * self.cell_width, y2 * self.cell_height, self.cell_width, self.cell_height)
        return None
    
    def total_width(self):
        return self.cell_width * self.width
    
    def total_height(self):
        return self.cell_height * self.height

    def print(self):
        acc = 0
        for i in range(self.width * self.height):
            print(self.tiles[i], end="")
            acc += 1
            if acc == self.width:
                print("")
                acc = 0

# Particles are very simple, they are just a speed, lifetime, and texture
class Particle:
    def __init__(self, x: float, y: float, h_speed: float, v_speed: float, lifetime: int, tex: kn.Texture):
        self.x = x
        self.y = y
        self.h_speed = h_speed
        self.v_speed = v_speed
        self.tex = tex
        self.lifetime = lifetime
        self.max_life = lifetime

    # returns true if this things life is up
    def draw(self, accelerate_x: float, accelerate_y: float) -> bool:
        self.h_speed += accelerate_x
        self.v_speed += accelerate_y
        self.x += self.h_speed
        self.y += self.v_speed
        self.lifetime -= 1
        self.tex.alpha = self.lifetime / self.max_life
        kn.renderer.draw(self.tex, (self.x, self.y))
        return self.lifetime <= 0

def clamp(val, min, max):
    if val > max: return max
    if val < min: return min
    return val

def sign(val):
    if val > 0: return 1
    if val < 0: return -1
    return 0

def main():
    game_width = 400
    game_height = 288
    kn.init()
    kn.window.create("Game Window", (game_width, game_height), scaled=True)
    kn.time.set_target(60)

    # Load assets
    level_tmx = kn.TileMap("assets/level.tmx")
    ground_layer = level_tmx.get_layer("ground")
    decoration_layer = level_tmx.get_layer("decoration")
    player_animations = kn.AnimationController()
    player_animations.load_sprite_sheet("player_idle_right", "assets/player_idle_right.png", (16, 16), 2)
    player_animations.load_sprite_sheet("player_idle_left", "assets/player_idle_left.png", (16, 16), 2)
    player_animations.load_sprite_sheet("player_walk_right", "assets/player_walk_right.png", (16, 16), 10)
    player_animations.load_sprite_sheet("player_walk_left", "assets/player_walk_left.png", (16, 16), 10)
    player_animations.load_sprite_sheet("player_jump_right", "assets/player_jump_right.png", (16, 16), 20)
    player_animations.load_sprite_sheet("player_jump_left", "assets/player_jump_left.png", (16, 16), 20)
    player_animations.load_sprite_sheet("player_jump_right_first", "assets/player_jump_right_first.png", (16, 16), 20)
    player_animations.load_sprite_sheet("player_jump_left_first", "assets/player_jump_left_first.png", (16, 16), 20)
    tex_ground_part = kn.Texture("assets/ground_part.png")
    aud_jump = kn.Audio("assets/jump.wav", 0.45)
    aud_walk = kn.Audio("assets/walk.wav", 0.30)
    aud_land = kn.Audio("assets/land.wav", 0.30)

    # Info for parallaxing backgrounds
    tex_bg_layers = [
        kn.Texture("assets/sun.png"),
        kn.Texture("assets/layer_mountains.png"),
        kn.Texture("assets/layer1.png"),
        kn.Texture("assets/layer2.png"),
        kn.Texture("assets/layer3.png"),
    ]
    bg_layer_parallaxes = [
        0.999, 
        0.99,
        0.95, 
        0.9, 
        0.7
    ]

    # These will be drawn on top of the level
    tex_fg_layers = [
        kn.Texture("assets/foreground1.png"),
    ]
    fg_layer_parallaxes = [
        -0.7,
    ]
    camera = kn.Camera()

    # Player
    player_x = 100
    player_y = 100
    player_hitbox = kn.Rect(2, 1, 12, 15)

    # Variables relating to platforming physics and QoL
    gravity = 0.65 # gravity acceleration
    max_gravity = 10 # max gravity speed
    h_speed = 0 # horizontal speed
    v_speed = 0 # vertical speed
    acceleration = 0.6 # horizontal acceleration
    friction = 0.8 # friction applied when player is not giving input to gradually slow down
    top_speed = 5 # top horizontal speed
    initial_jump_speed = 4 # initial jump velocity
    just_pressed_timer = 0
    just_pressed_timer_duration = 8 # how many additional frames they can hold down jump
    jump_increase_velocity = 0.25 # additional velocity per frame for holding down jump
    jump_grace_frames = 5 # how many frames after the player leaves a platform can they still jump
    jump_grace_duration = 0
    extra_jumps = 1 # amount of extra jumps the player gets (1 is double jump)
    current_extra_jumps = 0
    facing = 1 # which way the player is facing, -1 = left, 1 = right
    in_extra_jump = False # for unique double jump animations

    # For sfx and particles
    frame_timer = 0
    walk_timer = 12 # one in every <x> frames the walk sound effect is played
    particles = []

    # Really basic particle spawner that randomly places particles with a given direction and spread
    def spawn_particles(count: int, lifetime: int, x: float, y: float, angle: float, speed: float, spread: float, tex: kn.Texture):
        for i in range(count):
            dir = angle + rand(-spread / 2, spread / 2)
            p = Particle(x, y, cos(dir) * speed, sin(dir) * speed, lifetime, tex)
            particles.append(p)
    
    # We are using tilemap-based collisions, and KrakenEngine currently does not support getting
    # the tilemap data from the raw tiled file, so we manually extract it from the .tmx file here.
    # This is just one possible way to approach this problem.
    tilemap = TileMap(200, 18, 16, 16)
    tree = ET.parse("assets/level.tmx")
    root = tree.getroot()
    data = root.find(".//layer[@name='ground']/data").text.strip()
    tiles = [int(x) for x in data.replace("\n", "").split(",") if x.strip()]
    acc = 0
    y = 0
    for i in range(len(tiles)):
        tilemap.set(acc, y, tiles[i])
        acc += 1
        if acc == 200:
            acc = 0
            y += 1

    # Main game loop
    while kn.window.is_open():
        kn.event.poll()
        camera.set()

        ################################ Player controls ################################
        # To make the platforming feel fluid and fun there are a few key things we do   #
        #   1. Horizontal movement is done by acceleration, NOT just speed.             #
        #   2. Jumping is an initial vertical speed, then the player may hold jump      #
        #      down for a moment longer to increase jump height.                        #
        #   3. We briefly will allow the player to still jump after leaving a platform. #
        # These three things combine to make a very fluid-feeling platformer. Applying  #
        # acceleration instead of speed horizontally can give just enough of a feeling  #
        # that you're controlling a character and not a mechanical arm, letting players #
        # control jump height via holding jump longer allows for more precise           #
        # platforming challenges, and allowing a brief moment where the player may      #
        # still jump after leaving a platform makes the player feel like their inputs   #
        # aren't being dropped. All of these things are being controlled by the         #
        # variables above, change them to see how it changes the game.                  #
        #################################################################################

        # Apply player acceleration, if left and right are held down it adds to 0
        current_acc = 0
        if kn.key.is_pressed(kn.Scancode.S_LEFT): current_acc -= acceleration
        if kn.key.is_pressed(kn.Scancode.S_RIGHT): current_acc += acceleration

        # Cap the top player speed and only apply friction if the player isn't moving
        h_speed = clamp(h_speed + current_acc, -top_speed, top_speed)
        if h_speed != 0 and current_acc == 0:
            if sign(h_speed - (sign(h_speed) * friction)) != sign(h_speed):
                h_speed = 0
            else:
                h_speed -= sign(h_speed) * friction

        # Gravity
        v_speed = clamp(v_speed + gravity, -max_gravity, max_gravity)

        # Facing is used to make the player animations face the right way
        if current_acc < 0:
            facing = -1
        elif current_acc > 0:
            facing = 1

        # Allows the player to still jump for a small period after leaving a platform
        if tilemap.colliding(player_x, player_y + 1, player_hitbox):
            # Player just landed, play sound and particle effects
            if jump_grace_duration <= 0: 
                kn.Audio.play(aud_land)
                spawn_particles(10, 15, player_x + 8, player_y + 16, -3.14 / 2, 4, 3.14 / 4, tex_ground_part)
            jump_grace_duration = jump_grace_frames
            current_extra_jumps = extra_jumps
            in_extra_jump = False
        jump_grace_duration -= 1
        
        # Allows the player to jump higher if they hold jump down
        if kn.key.is_pressed(kn.Scancode.S_UP) and just_pressed_timer > 0:
            v_speed -= jump_increase_velocity + gravity

        # Initial jump press
        if kn.key.is_just_pressed(kn.Scancode.S_UP) and (jump_grace_duration > 0 or current_extra_jumps > 0):
            v_speed = -initial_jump_speed
            just_pressed_timer = just_pressed_timer_duration
            kn.Audio.play(aud_jump)
            if jump_grace_duration <= 0: 
                current_extra_jumps -= 1
                in_extra_jump = True
        just_pressed_timer -= 1

        ######################## General purpose collisions ########################
        # These work by checking if the player is about to walk into a wall, and   #
        # if so we move the player as close to the wall as possible without being  #
        # inside the wall. For rounding purposes, there are some 0.01's scattered  #
        # around, remove them to see the difference they make.                     #
        ############################################################################
        collider = tilemap.colliding_with(player_x + h_speed, player_y - 0.01, player_hitbox)
        if not collider is None:
            if h_speed > 0:
                player_x = collider.x - (player_hitbox.w + player_hitbox.x + 0.01)
            elif h_speed < 0:
                player_x = collider.right - player_hitbox.x
            h_speed = 0
        player_x += h_speed

        # Same thing but vertically
        collider = tilemap.colliding_with(player_x, player_y + v_speed, player_hitbox)
        if not collider is None:
            if v_speed > 0:
                player_y = collider.y - (player_hitbox.h + player_hitbox.y)
            elif h_speed < 0:
                player_y = collider.bottom - player_hitbox.y + 0.01
            v_speed = 0
        player_y += v_speed

        # If the player is moving at at least 15% top speed and on the ground we play a walking sound effect
        # once every walk_timer frames.
        if frame_timer % walk_timer == 0 and abs(h_speed) > top_speed * 0.15 and jump_grace_duration > 0:
            kn.Audio.play(aud_walk)

        # Background colour is a sky blue
        kn.renderer.clear(kn.color.from_hex("#9feaec"))
        
        # This function is to make drawing tiling backgrounds easier
        def tile_horizontally(t: kn.Texture, x: float):
            t_rect = t.get_rect()
            t_width = float(t_rect.w)
            view_left = camera.pos.x - (game_width / 2)
            view_right = view_left + game_width
            start_x = x + floor((view_left - x) / t_width) * t_width
            tiles_needed = int(ceil((view_right - start_x) / t_width)) + 2

            for i in range(tiles_needed):
                draw_x = start_x + i * t_width
                kn.renderer.draw(t, kn.Rect(draw_x, 0, t_rect.w, t_rect.h))

        
        ################################## Parallax Layers ##################################
        # Parallax layers are done by drawing backgrounds relative to the camera multiplied #
        # by a parallax constant from 0-1. Using values closer to 1 gives the illision of   #
        # farther objects while values near 0 are closer to the foreground. Negative values #
        # appear to be in front of the foreground. We use a function to tile backgrounds so #
        # we don't need to worry about drawing multiple to cover the screen.                #
        #####################################################################################
        for (para, tex_layer) in zip(bg_layer_parallaxes, tex_bg_layers):
            tile_horizontally(tex_layer, camera.pos.x * para)

        # Draw level from the tiled level file
        ground_layer.render()
        decoration_layer.render()

        # Foreground layers are also parallax but in front of the level
        for (para, tex_layer) in zip(fg_layer_parallaxes, tex_fg_layers):
            tile_horizontally(tex_layer, camera.pos.x * para)

        # Choose which animation we need to play for the player based on
        #   1. Are they mid-air?
        #     a) If they are, are they on the double jump?
        #   2. Are they walking or idling?
        #   3. Which way are they facing?
        if facing == -1:
            if v_speed != 0:
                player_animations.set("player_jump_left" if in_extra_jump else "player_jump_left_first")
            elif h_speed != 0:
                player_animations.set("player_walk_left")
            else:
                player_animations.set("player_idle_left")
        else:
            if v_speed != 0:
                player_animations.set("player_jump_right" if in_extra_jump else "player_jump_right_first")
            elif h_speed != 0:
                player_animations.set("player_walk_right")
            else:
                player_animations.set("player_idle_right")
        frame = player_animations.current_frame
        kn.renderer.draw(frame.tex, kn.Rect(player_x, player_y, 16, 16), frame.src)

        # Particles all have a set lifetime, so we keep track of each particle that has
        # reached the end of its lifetime in the kill_list, then we go through the kill
        # list after updating/drawing particles and remove them from the particle list.
        kill_list = []
        for p in particles:
            if p.draw(0, gravity):
                kill_list += [p]
        for p in kill_list:
            particles.remove(p)

        # We center the camera on the player and slowly ease the camera towards that point, instead of instantly
        # snapping it on the player.
        target_x = player_x - (400 / 2)
        target_y = player_y - (288 / 2)
        camera.pos = (clamp(camera.pos.x + (target_x - camera.pos.x) * 0.25, 0, tilemap.total_width() - 400), 
                      clamp(camera.pos.y + (target_y - camera.pos.y) * 0.25, 0, tilemap.total_height() - 288))
        
        kn.renderer.present()
        frame_timer += 1

if __name__ == "__main__":
    main()