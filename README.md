# Introduction
This implementation of motion activated lighting implements a finite state machine to ensure that `MotionLight`s do not interfere with the rest of your home automation setup.

![State Machine](images/state_machine_diagram.png)

# Configuration
The app is quite configurable. In its most basic form, you can define the following.

*Basic Configuration**
MotionLight needs a `binary_sensor` to monitor as well as an entity to control.

```yaml
motion_light:
  module: motion_lights
  class: MotionLights
  sensor: binary_sensor.living_room_motion  # required
  entity_on: light.table_lamp               # required
  delay: 300                                # optional, overwrites default delay of 180s
```

**Using AppDaemon Constraints**
You may wish to constrain at what time of day your MOtionLights are activated. You can use AppDaemon's contraint mechanism for this.
```yaml
motion_light:
  module: motion_lights
  class: MotionLights
  sensor: binary_sensor.living_room_motion
  entity_on: light.table_lamp
  constrain_start_time: sunset - 00:00:00
  constrain_end_time: sunrise + 00:30:00
```
**Advanced Parameters**
```yaml
motion_light:
  module: motion_lights
  class: MotionLights
  sensor: binary_sensor.living_room_motion
  entity_on: light.tv_led                   # LED strip supports `brightness`
  brightness: 80                            # Go to 80% brightness
```

## Night Mode
Night mode allows you to use slightly different parameters at night. The use case for this is that you may want to use a shorter `delay` interval at night as people are typically asleep and the light may only need to stay on for a minute. Adjusting a custom night time brightness is useful as well.

```yaml
motion_light:
  module: motion_lights
  class: MotionLights
  sensor: binary_sensor.living_room_motion
  entity_on: light.tv_led
  delay: 300
  brightness: 80
  night_mode:
    delay: 60
    brightness: 20
    start_time: '22:00:00'                  # required
    end_time: '07:00:00'                    # required
```

## Advanced Configuration


**Calling custom scripts**
If you wish to use custom scripts rather than a `light` entity. This is the case when the `entity_on` entity does not support a `turn_off` service call. You can define `entity_on` and `entity_off`. MotionLight will call the `turn_on` service on both.

```yaml
motion_light:
  module: motion_lights
  class: MotionLights
  sensor: binary_sensor.living_room_motion
  entity_on: script.fade_in_led             # required
  entity_off: script.fade_out_led           # required if `turn_off` does not work on `entity_on`
  
```

