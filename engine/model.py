import math
import os
import pygame
import json

from .logger import Log

if not pygame.get_init():
    pygame.init()

class Model:
    def __init__(self, path):
        self.__path = path

        self.frames = []
        self.animations = {}
        self.animation_state = None
        self.has_blink = False
        self.blink_duty = -1
        self.blink_length = -1
        self.is_visible = True

        self.frame_index = 0
        self.last_step_time = 0
        self.last_frame_change_time = 0
        self.last_blink_time = 0

        self.__rotation = 0

        self.blink_frame = self.__create_blink_frame()

        self.__load()
        Log.log(f"Loaded Model From {self.__path}")

    def __create_blink_frame(self):
        return pygame.Surface((1, 1), pygame.SRCALPHA)

    def __load_frame(self, path: str) -> pygame.Surface:
        return pygame.image.load(path).convert_alpha()

    def __load(self):
        self.frames = []
        self.animations = {}

        model_data = json.load(open(self.__path))
        frame_paths = model_data['frames']

        for frame_path in frame_paths:
            if not os.path.exists(frame_path):
                raise FileNotFoundError(f'File not found while loading model: "{frame_path}" in "{self.__path}"')

            self.frames.append(self.__load_frame(frame_path))

        for state in model_data['animations']:
            if state in self.animations:
                print(f"[WARNING] Model: Overriding animation state '{state}' in '{self.__path}'")

            state_data = model_data['animations'][state]

            frame_indexes = state_data['indexes']
            frame_count = len(frame_indexes)

            loop_time_s = state_data['loop_time']

            step_delta_time = loop_time_s / frame_count

            self.animations[state] = {
                "delta": step_delta_time,
                "indexes": frame_indexes,
                "end": loop_time_s
            }

        if len(self.animations) == 0:
            raise ValueError("Must have at least one animation state within a model")

        if "default" in model_data:
            self.set_animation(model_data["default"])
        else:
            self.set_animation(list(self.animations.keys())[0])

        if "blink" in model_data:
            self.has_blink = True
            self.blink_duty = float(model_data["blink"]["duty"])
            self.blink_length = float(model_data["blink"]["length"])

    def __get_current_animation(self):
        assert self.animation_state is not None, "Model must have an animation state"
        return self.animations[self.animation_state]

    def set_animation(self, state: str):
        if state != self.animation_state:
            self.animation_reset()

            if state not in self.animations:
                raise ValueError(f"Animation state '{state}' not found in model")

            self.animation_state = state

    def set_rotation(self, rotation: float):
        self.__rotation = math.degrees(rotation)

    def animation_reset(self):
        self.frame_index = 0
        self.last_step_time = 0
        self.last_frame_change_time = 0
        self.last_blink_time = 0
        self.is_visible = True

    def step(self, deltaTime: float):
        animation = self.__get_current_animation()

        self.last_step_time += deltaTime

        if self.has_blink:
            blink_delta = self.last_step_time - self.last_blink_time
            current_duty = self.blink_duty if self.is_visible else 1 - self.blink_duty
            
            if blink_delta > self.blink_length * current_duty:
                self.last_blink_time = self.last_step_time
                self.is_visible = not self.is_visible

        if self.last_step_time > self.last_frame_change_time + animation['delta']:
            self.last_frame_change_time = self.last_step_time
            self.frame_index = (self.frame_index + 1) % len(animation["indexes"])

    def get_frame(self, index: int) -> pygame.Surface:
        return self.frames[index]

    def get_current(self):
        if self.is_visible:
            frame = self.get_frame(self.frame_index)

            if self.__rotation == 0:
                return frame

            else:
                return pygame.transform.rotate(frame, -self.__rotation)

        return self.blink_frame
