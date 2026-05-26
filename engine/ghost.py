import random
from .ghost_names import *
from .model import Model

class GenericGhost:
    # Ghost Movement / Hunts
    WALK_SPEED = 1.1
    LINE_OF_SIGHT_SPEED = 1.5
    LIGHTS_ON_SPEED_MULTIPLIER = 1.1

    # How Ghost Looks
    MODEL_TYPE = "any"  # "any" -> "female", "male"
    VISIBILITY = 0.5

    # Ghosts perceptions
    VISION = 1
    AUDIO = 1
    ELECTRONICS = 1

    CAN_SEE_IN_HIDING_SPOTS = False
    IS_BLINDED_BY_LIGHTS = False

    HUNT_SANITY = 50

    # Evidence / Behaviours -> Ghosts can have 3-4 evidences, 1-2 generic, 2 non-generic
    EVIDENCE_EMF = False            # Generic evidences
    EVIDENCE_DOTS = False
    EVIDENCE_COLD = False
    EVIDENCE_HOT = False
    EVIDENCE_UV = False

    EVIDENCE_WHISPERS = False       # Directional Audio -> Select player only
    EVIDENCE_STATIC = False         # Radios Glitching without a "hunt"
    EVIDENCE_HEARTBEAT = False      # Proximity pulsing sound, maybe only over the radio?
    EVIDENCE_STALKING = False       # Only hunts/sees 1 player until they are dead
    EVIDENCE_ISOLATION = False      # Can only interact when the room is empty
    EVIDENCE_TIMELOSS = False       # Can desync the time for each player (Each player has a watch / timer)
    EVIDENCE_DOPPELGANGER = False   # Can cause an event where it mimics the appearnce of a player (dead or alive)

    def __init__(self, load=True):
        if load:
            if self.MODEL_TYPE == "any":
                self.MODEL_TYPE = random.choice(["male", "female"])

            self.model = Model(f"data/models/ghosts/{self.MODEL_TYPE}{random.randint(1, 1)}.json")

            self.first_name = random.choice(MALE_NAMES if self.MODEL_TYPE == "male" else FEMALE_NAMES)
            self.last_name = random.choice(LAST_NAMES)

        self.active_evidence = [
            attr_name
            for attr_name, value in vars(self).items()
            if attr_name.startswith("EVIDENCE_") and value is True
        ]



class Static(GenericGhost):
    VISION = 0.8
    AUDIO = 1
    ELECTRONICS = 1.5

    HUNT_SANITY = 45

    EVIDENCE_EMF = True
    EVIDENCE_STATIC = True
    EVIDENCE_TIMELOSS = True


class Krasue(GenericGhost):
    WALK_SPEED = 1.6
    LIGHTS_ON_SPEED_MULTIPLIER = 1.5

    VISION = 1.3
    AUDIO = 1
    ELECTRONICS = 0.2

    IS_BLINDED_BY_LIGHTS = True
    HUNT_SANITY = 70

    EVIDENCE_EMF = True
    EVIDENCE_HEARTBEAT = True
    EVIDENCE_STALKING = True


class Ghost3(GenericGhost):
    WALK_SPEED = 0.8
    LINE_OF_SIGHT_SPEED = 1.1
    LIGHTS_ON_SPEED_MULTIPLIER = 0.5

    CAN_SEE_IN_HIDING_SPOTS = True

    VISION = 1
    AUDIO = 2
    ELECTRONICS = 1

    EVIDENCE_UV = True
    EVIDENCE_COLD = True
    EVIDENCE_WHISPERS = True
    EVIDENCE_HEARTBEAT = True


class Ghost4(GenericGhost):
    WALK_SPEED = 0.8
    LINE_OF_SIGHT_SPEED = 2.5

    VISION = 1.5
    AUDIO = 0.7
    ELECTRONICS = 0.7

    HUNT_SANITY = 70
    VISIBILITY = 0.75

    EVIDENCE_DOTS = True
    EVIDENCE_DOPPELGANGER = True
    EVIDENCE_HEARTBEAT = True


class Ghost5(GenericGhost):
    WALK_SPEED = 1.1
    LINE_OF_SIGHT_SPEED = 1.5
    LIGHTS_ON_SPEED_MULTIPLIER = 1.5

    MODEL_TYPE = "female"
    VISIBILITY = 0.25

    HUNT_SANITY = 30

    EVIDENCE_HOT = True
    EVIDENCE_WHISPERS = True
    EVIDENCE_ISOLATION = True