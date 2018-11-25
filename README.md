# Introduction
This implementation of motion activated lighting implements a finite state machine to ensure that `MotionLight`s do not interfere with the rest of your home automation setup.

![State Machine](images/state_machine_diagram.png)
# Requirements
Motion lights have the following requirements (R) that I discussed in detail [on my blog](https://www.danielha.tk/2018/05/17/appdaemon-motion-lights.html).

1. turn on when motion is detected
2. turn off when no motion is detected after some timeout
3. Do not interfere with manually activated lights (tricky and less than obvious)

That last one can be separated into the following two requirements:

3.1 A light that is already on should not be affected by time outs.
3.2 A light that is switched on within the time-out period should have its timer cancelled, and therefore stay on.

This AppDaemon app is by far the most elegant solution I have found for this problem.

# Configuration
The app is quite configurable. In its most basic form, you can define the following.

*Basic Configuration**
`MotionLight` needs a `binary_sensor` to monitor as well as an entity to control.

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

You may use custom scripts to control a `light` entity with more precision. This is the case when the `entity_on` entity does not support a `turn_off` service call or use want to pass custom service parameters to the service call. You can define `entity_on` and `entity_off`. The `MotionLight` will call the `turn_on` service on both and observe the state using `entity`.

```yaml
motion_light:
  module: motion_lights
  class: MotionLights
  sensor: binary_sensor.living_room_motion
  entity: light.led                         # required
  entity_on: script.fade_in_led             # required
  entity_off: script.fade_out_led           # required if `turn_off` does not work on `entity_on`
  
```

**MQTT Topic (to be implemented)**

Supplying the top-level `topic` parameter allows the MotionLight to react to MQTT messages. This is used to cancel any pending motion timeouts when the entity is controlled through some other means, for example another automation (refer to state diagram `CONTROL_COMMAND` event). This mechanism is yet to be implemented and tested.

```yaml
motion_light:
  module: motion_lights
  class: MotionLights
  sensor: binary_sensor.living_room_motion # required
  entity_on: light.table_lamp
  topic: "cmnd/table_lamp/POWER"
```