from math import ceil, cos, floor, sin
import pykraken as kn
import xml.etree.ElementTree as ET
from random import uniform as rand

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
    
    def colliding(self, hitbox: kn.Rect) -> bool:
        x1 = floor(hitbox.x / self.cell_width)
        y1 = floor(hitbox.y / self.cell_height)
        x2 = floor((hitbox.x + hitbox.w) / self.cell_width)
        y2 = floor((hitbox.y + hitbox.h) / self.cell_height)
        return (
            self.get(x1, y1) != 0 or
            self.get(x2, y1) != 0 or
            self.get(x1, y2) != 0 or
            self.get(x2, y2) != 0
        )
    
    def colliding_with(self, hitbox: kn.Rect) -> any:
        if self.get(floor(hitbox.x / self.cell_width), floor(hitbox.y / self.cell_height)) != 0: return (floor(hitbox.x / self.cell_width), floor(hitbox.y / self.cell_height))
        if self.get(floor((hitbox.x + hitbox.w) / self.cell_width), floor(hitbox.y / self.cell_height)) != 0: return (floor((hitbox.x + hitbox.w) / self.cell_width), floor(hitbox.y / self.cell_height))
        if self.get(floor(hitbox.x / self.cell_width), floor((hitbox.y + hitbox.h) / self.cell_height)) != 0: return (floor(hitbox.x / self.cell_width), floor((hitbox.y + hitbox.h) / self.cell_height))
        if self.get(floor((hitbox.x + hitbox.w) / self.cell_width), floor((hitbox.y + hitbox.h) / self.cell_height)) != 0: return (floor((hitbox.x + hitbox.w) / self.cell_width), floor((hitbox.y + hitbox.h) / self.cell_height))
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
    kn.init()
    kn.window.create("Game Window", (400, 288), scaled=True)
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
    tex_bg_layers = [
        kn.Texture("assets/sun.png"),
        kn.Texture("assets/layer1.png"),
        kn.Texture("assets/layer2.png"),
        kn.Texture("assets/layer3.png"),
    ]
    camera = kn.Camera()

    # Gameplay variables
    player_x = 100
    player_y = 100
    player_w = 16
    player_h = 16
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
    walk_timer = 12 # one in every <x> frames the walk sound effect is played
    frame_timer = 0
    particles = []

    def spawn_particles(count: int, lifetime: int, x: float, y: float, angle: float, speed: float, spread: float, tex: kn.Texture):
        for i in range(count):
            dir = angle + rand(-spread / 2, spread / 2)
            p = Particle(x, y, cos(dir) * speed, sin(dir) * speed, lifetime, tex)
            particles.append(p)
    
    # Create tilemap from tiled
    tilemap = TileMap(100, 18, 16, 16)
    tree = ET.parse("assets/level.tmx")
    root = tree.getroot()
    data = root.find(".//layer[@name='ground']/data").text.strip()
    tiles = [int(x) for x in data.replace("\n", "").split(",") if x.strip()]
    acc = 0
    y = 0
    for i in range(len(tiles)):
        tilemap.set(acc, y, tiles[i])
        acc += 1
        if acc == 100:
            acc = 0
            y += 1

    while kn.window.is_open():
        kn.event.poll()
        camera.set()

        # Player movement
        current_acc = 0
        if kn.key.is_pressed(kn.Scancode.S_LEFT): current_acc -= acceleration
        if kn.key.is_pressed(kn.Scancode.S_RIGHT): current_acc += acceleration

        # Apply acceleration and friction
        h_speed = clamp(h_speed + current_acc, -top_speed, top_speed)
        if h_speed != 0 and current_acc == 0:
            if sign(h_speed - (sign(h_speed) * friction)) != sign(h_speed):
                h_speed = 0
            else:
                h_speed -= sign(h_speed) * friction
        v_speed = clamp(v_speed + gravity, -max_gravity, max_gravity)

        # Turn player left/right
        if current_acc < 0:
            facing = -1
        elif current_acc > 0:
            facing = 1

        # Allows the player to still jump for a small period after leaving a platform
        if tilemap.colliding(kn.Rect(player_x, player_y + 1, player_w, player_h)):
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

        # Collisions
        if tilemap.colliding(kn.Rect(player_x + h_speed, player_y - 0.01, player_w, player_h)):
            while not tilemap.colliding(kn.Rect(player_x + sign(h_speed), player_y - 0.01, player_w, player_h)):
                player_x += sign(h_speed)
            h_speed = 0
        player_x += h_speed
        if tilemap.colliding(kn.Rect(player_x, player_y + v_speed, player_w, player_h)):
            #_, tile_y = tilemap.colliding_with(kn.Rect(player_x, player_y + v_speed, player_w, player_h))
            #if v_speed > 0:
            #    player_y = (tile_y * 16) - 16
            #else:
            #    player_y = (tile_y * 16)
            while not tilemap.colliding(kn.Rect(player_x, player_y + sign(v_speed), player_w, player_h)):
                player_y += sign(v_speed) * 0.1
            v_speed = 0
        player_y += v_speed

        # Walking sound effect
        if frame_timer % walk_timer == 0 and abs(h_speed) > top_speed * 0.15 and jump_grace_duration > 0:
            kn.Audio.play(aud_walk)

        # Draw background
        kn.renderer.clear(kn.color.from_hex("#7bb9b9"))
        def tile_horizontally(t: kn.Texture, x: float):
            for i in range(ceil(tilemap.total_width() / t.get_rect().w)):
                kn.renderer.draw(t, kn.Rect((x + (i * t.get_rect().w)) - (i + 1), 0, t.get_rect().w, t.get_rect().h))
        for (para, tex_layer) in zip([0.99, 0.9, 0.85, 0.7], tex_bg_layers):
            tile_horizontally(tex_layer, camera.pos.x * para)

        # Draw ground tilemap
        ground_layer.render()
        decoration_layer.render()

        # Draw player
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

        # Draw particles
        kill_list = []
        for p in particles:
            if p.draw(0, gravity):
                kill_list += [p]
        for p in kill_list:
            particles.remove(p)

        # Camera should follow player
        target_x = player_x - (400 / 2)
        target_y = player_y - (288 / 2)
        camera.pos = (clamp(camera.pos.x + (target_x - camera.pos.x) * 0.25, 0, tilemap.total_width() - 400), 
                      clamp(camera.pos.y + (target_y - camera.pos.y) * 0.25, 0, tilemap.total_height() - 288))
        
        kn.renderer.present()
        frame_timer += 1

if __name__ == "__main__":
    main()