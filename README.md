# Chest-Minigame-Deku-Clip

- one big limitation of this script currently is that it fails for angles like 0x38ff where if you target and then untarget and then wait long enough, the camera angle will increment to 0x4000. this sort of camera behavior is properly accounted for for angle like 0xff90, though the behavior is a little different in the corresponding angle range (but was necessary to get working because we use this range for the actual deku spin clip and the deku spin is untargeted meaning the camera can update)
