# Introduction
Entity Controller (EC) is an implementation of "When This, Then That" using a finite state machine that ensures basic automations do not interfere with the rest of your home automation setup. This component encapsulates common automation scenarios into a neat package that can be configured easily and reused throughout your home. Traditional automations would need to be duplicated _for each instance_ in your config. The use cases for this component are endless because you can use any entity as input and outputs (there is no restriction to motion sensors and lights).


![Entity Controller State Diagram](https://github.com/danobot/entity-controller/blob/master/images/state_diagram.png?raw=true)

## Basic Configuration
The controller needs `sensors` to monitor (such as motion detectors, binary switches, doors, weather, etc) as well as an entity to control (such as a light).

```yaml
entity_controller:
  motion_light:                               # serves as a name
    sensor: binary_sensor.living_room_motion  # required, [sensors]
    entity: light.table_lamp                  # required, [entity,entities]
    delay: 300                                # optional, overwrites default delay of 180s
```

[Buy me a coffee to support ongoing development](https://www.gofundme.com/danobot&rcid=r01-155117647299-36f7aa9cb3544199&pc=ot_co_campmgmt_w)

[Documentation](https://github.com/danobot/entity-controller)