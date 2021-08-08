# Change Log

All notable changes to this project will be documented in this file. See [standard-version](https://github.com/conventional-changelog/standard-version) for commit guidelines.

<a name="9.2.9"></a>
## [9.2.9](https://github.com/danobot/entity-controller/compare/v9.2.8...v9.2.9) (2021-06-11)


### Bug Fixes

* upgrade transitions version to 0.8.8 ([88399ad](https://github.com/danobot/entity-controller/commit/88399ad))



<a name="9.2.8"></a>
## [9.2.8](https://github.com/danobot/entity-controller/compare/v9.2.7...v9.2.8) (2021-06-11)



<a name="9.2.7"></a>
## [9.2.7](https://github.com/danobot/entity-controller/compare/v9.2.6...v9.2.7) (2021-06-11)



<a name="9.2.6"></a>
## [9.2.6](https://github.com/danobot/entity-controller/compare/v9.2.5...v9.2.6) (2021-06-11)



<a name="9.2.5"></a>
## [9.2.5](https://github.com/danobot/entity-controller/compare/v9.2.4...v9.2.5) (2021-06-11)


### Bug Fixes

* upgrade transitions version to 0.8.8 ([#251](https://github.com/danobot/entity-controller/issues/251)) ([de9c954](https://github.com/danobot/entity-controller/commit/de9c954))



<a name="9.2.4"></a>
## [9.2.4](https://github.com/danobot/entity-controller/compare/v9.2.3...v9.2.4) (2021-05-25)


### Bug Fixes

* Version key ([#243](https://github.com/danobot/entity-controller/issues/243)) ([dc1f1ec](https://github.com/danobot/entity-controller/commit/dc1f1ec))



<a name="9.2.3"></a>
## [9.2.3](https://github.com/danobot/entity-controller/compare/v9.2.2...v9.2.3) (2021-05-04)


### Bug Fixes

* Version key ([#243](https://github.com/danobot/entity-controller/issues/243)) ([#245](https://github.com/danobot/entity-controller/issues/245)) ([6feef36](https://github.com/danobot/entity-controller/commit/6feef36))



<a name="9.2.2"></a>
## [9.2.2](https://github.com/danobot/entity-controller/compare/v9.2.1...v9.2.2) (2021-04-28)


### Bug Fixes

* Version key ([#243](https://github.com/danobot/entity-controller/issues/243)) ([#244](https://github.com/danobot/entity-controller/issues/244)) ([e2d7670](https://github.com/danobot/entity-controller/commit/e2d7670))



<a name="9.2.1"></a>
## [9.2.1](https://github.com/danobot/entity-controller/compare/v9.2.0...v9.2.1) (2021-02-04)


### Bug Fixes

* error messages used wrong variable ([9f20fb5](https://github.com/danobot/entity-controller/commit/9f20fb5))
* warn about potential configuration errors (could also mean entity is still initialising after reboot) ([7545d2e](https://github.com/danobot/entity-controller/commit/7545d2e))



<a name="9.2.0"></a>
# [9.2.0](https://github.com/danobot/entity-controller/compare/v9.1.0...v9.2.0) (2020-12-04)


### Bug Fixes

* HA does not need to poll EC for state ([#220](https://github.com/danobot/entity-controller/issues/220)) ([e8b833d](https://github.com/danobot/entity-controller/commit/e8b833d))
* missing service exceptions during startup ([#221](https://github.com/danobot/entity-controller/issues/221)) ([48d5602](https://github.com/danobot/entity-controller/commit/48d5602))


### Features

* Use unique Contexts to track cause and effect ([#222](https://github.com/danobot/entity-controller/issues/222)) ([56302ff](https://github.com/danobot/entity-controller/commit/56302ff))



<a name="9.1.0"></a>
# [9.1.0](https://github.com/danobot/entity-controller/compare/v9.0.2...v9.1.0) (2020-10-16)


### Features

* Allow 'ignored_event_sources' to contain Regex patterns to support integrations with dynamic context ids ([34df56e](https://github.com/danobot/entity-controller/commit/34df56e)), closes [/github.com/home-assistant/core/pull/40626#issuecomment-709373896](https://github.com//github.com/home-assistant/core/pull/40626/issues/issuecomment-709373896)



<a name="9.0.2"></a>
## [9.0.2](https://github.com/danobot/entity-controller/compare/v9.0.1...v9.0.2) (2020-10-12)


### Bug Fixes

* Context ID too long for recorder component [#200](https://github.com/danobot/entity-controller/issues/200) ([#203](https://github.com/danobot/entity-controller/issues/203)) ([a83ef05](https://github.com/danobot/entity-controller/commit/a83ef05))



<a name="9.0.1"></a>
## [9.0.1](https://github.com/danobot/entity-controller/compare/v9.0.0...v9.0.1) (2020-10-08)


### Bug Fixes

* include DOMAIN in Context id and log entire Context object for more detail ([bbc7b2e](https://github.com/danobot/entity-controller/commit/bbc7b2e))



<a name="9.0.0"></a>
# [9.0.0](https://github.com/danobot/entity-controller/compare/v8.0.0...v9.0.0) (2020-10-01)


### Features

* Implement Home Assistant Context API to avoid EC blocking itself (replaces grace_period) and ability to ignore event sources ([#193](https://github.com/danobot/entity-controller/issues/193)) ([738968d](https://github.com/danobot/entity-controller/commit/738968d)), closes [#192](https://github.com/danobot/entity-controller/issues/192) [#192](https://github.com/danobot/entity-controller/issues/192)


* fix!: Spelling of overridden ([0359947](https://github.com/danobot/entity-controller/commit/0359947))


### BREAKING CHANGES

* Fix the spelling of `on_enter_overidden` and `on_exit_overidden` to become `on_enter_overridden` and `on_exit_overridden` respectively.



<a name="8.0.0"></a>
# [8.0.0](https://github.com/danobot/entity-controller/compare/v7.0.0...v8.0.0) (2020-09-07)


### Features

* add customisable grace_period paramater to cater for long latencies in control entities ([b59d70c](https://github.com/danobot/entity-controller/commit/b59d70c))


* feat!: rename stay mode to make the feature easier to understand (#176) ([be46cb8](https://github.com/danobot/entity-controller/commit/be46cb8)), closes [#176](https://github.com/danobot/entity-controller/issues/176)


### BREAKING CHANGES

* Check the docs for new `stay_mode` configuration field and the name changes to the related services.



<a name="7.0.0"></a>
# [7.0.0](https://github.com/danobot/entity-controller/compare/v6.1.1...v7.0.0) (2020-09-04)


* feat!: rename stay mode to make the feature easier to understand (#176) (#177) ([9f7ec54](https://github.com/danobot/entity-controller/commit/9f7ec54)), closes [#176](https://github.com/danobot/entity-controller/issues/176) [#177](https://github.com/danobot/entity-controller/issues/177)


### BREAKING CHANGES

* Check the docs for new `stay_mode` configuration field and the name changes to the related services.



<a name="6.1.1"></a>
## [6.1.1](https://github.com/danobot/entity-controller/compare/v6.1.0...v6.1.1) (2020-09-03)


### Bug Fixes

* [#164](https://github.com/danobot/entity-controller/issues/164) active stay on never returning to idle state. ([75b1660](https://github.com/danobot/entity-controller/commit/75b1660))
* [#173](https://github.com/danobot/entity-controller/issues/173) call homeassistant.turn_on for groups ([afab88f](https://github.com/danobot/entity-controller/commit/afab88f))
* [#173](https://github.com/danobot/entity-controller/issues/173) include turn_off service and use the correct variable ([c54f2f0](https://github.com/danobot/entity-controller/commit/c54f2f0))
* [#174](https://github.com/danobot/entity-controller/issues/174) and [#98](https://github.com/danobot/entity-controller/issues/98) implements crude way to avoid getting blocked by ECs own service calls (and subsequent state changes) ([13f751b](https://github.com/danobot/entity-controller/commit/13f751b))
* add load-beta.sh script for loading files from develop branch ([67ec478](https://github.com/danobot/entity-controller/commit/67ec478))
* Fixes [#174](https://github.com/danobot/entity-controller/issues/174) and [#98](https://github.com/danobot/entity-controller/issues/98) where changing a control entity does not transition EC to blocked state (R3.2) ([f4c3275](https://github.com/danobot/entity-controller/commit/f4c3275))



<a name="6.1.0"></a>
# [6.1.0](https://github.com/danobot/entity-controller/compare/v6.0.1...v6.1.0) (2020-08-30)


### Bug Fixes

* Change mdi:timer* to mdi:timer*-outline in prep for HA 0.115 ([#172](https://github.com/danobot/entity-controller/issues/172)) ([9f019b8](https://github.com/danobot/entity-controller/commit/9f019b8))


### Features

* Transition Behaviours Extended ([#159](https://github.com/danobot/entity-controller/issues/159)) ([aa8dab9](https://github.com/danobot/entity-controller/commit/aa8dab9))



<a name="6.0.1"></a>
## [6.0.1](https://github.com/danobot/entity-controller/compare/v6.0.0...v6.0.1) (2020-08-30)



<a name="6.0.0"></a>
# [6.0.0](https://github.com/danobot/entity-controller/compare/v5.2.0...v6.0.0) (2020-06-20)


### Features

* transition behaviours and friendly name fix ([02a1ab4](https://github.com/danobot/entity-controller/commit/02a1ab4)), closes [#156](https://github.com/danobot/entity-controller/issues/156)


### BREAKING CHANGES

* The friendly name fix in #153 may break your configuration. Entities will be created based on the YAML section name but will respect friendly name in frontend.



<a name="5.2.0"></a>
# [5.2.0](https://github.com/danobot/entity-controller/compare/v5.1.2...v5.2.0) (2020-06-20)


### Bug Fixes

* BREAKING CHANGE ([2034e49](https://github.com/danobot/entity-controller/commit/2034e49))


### Features

* transition behaviours ([ffbbb47](https://github.com/danobot/entity-controller/commit/ffbbb47))
* transition behaviours  ([f85edc5](https://github.com/danobot/entity-controller/commit/f85edc5))



<a name="5.1.2"></a>
## [5.1.2](https://github.com/danobot/entity-controller/compare/v5.1.1...v5.1.2) (2020-04-05)



<a name="5.1.1"></a>
## [5.1.1](https://github.com/danobot/entity-controller/compare/v5.1.0...v5.1.1) (2020-04-05)



<a name="5.1.0"></a>
# [5.1.0](https://github.com/danobot/entity-controller/compare/v5.0.2...v5.1.0) (2020-03-02)


### Features

* basic services and control ([d1912b4](https://github.com/danobot/entity-controller/commit/d1912b4))
* Initial services buildout ([#142](https://github.com/danobot/entity-controller/issues/142)) ([e5e18f5](https://github.com/danobot/entity-controller/commit/e5e18f5))



<a name="5.0.2"></a>
## [5.0.2](https://github.com/danobot/entity-controller/compare/v5.0.1...v5.0.2) (2020-02-02)



<a name="5.0.1"></a>
## [5.0.1](https://github.com/danobot/entity-controller/compare/v5.0.0...v5.0.1) (2020-01-11)


### Bug Fixes

* remove trace logging ([b50f08b](https://github.com/danobot/entity-controller/commit/b50f08b))



<a name="5.0.0"></a>
# [5.0.0](https://github.com/danobot/entity-controller/compare/v4.2.0...v5.0.0) (2020-01-10)


* feat!: handle overrides better ([63f7aa8](https://github.com/danobot/entity-controller/commit/63f7aa8))


### BREAKING CHANGES

* Entering the override state will no longer turn off the control entities. This was implemented with the ratiionale that overriding an EC should not cause further interaction with the control entities. If the entities are on, they remain on when transitioning from active to override state. If the entities are off, they remain off going from other states in to override state.
If your configuration relied on this previous behaviour it will be a breaking change for you. Its unlikely your config took advantage of this weird behaviour.



<a name="4.2.0"></a>
# [4.2.0](https://github.com/danobot/entity-controller/compare/v4.1.6...v4.2.0) (2019-12-21)


### Features

* Allow customization of which attribute changes are considered a manual change, closes [#109](https://github.com/danobot/entity-controller/issues/109) ([#112](https://github.com/danobot/entity-controller/issues/112)) ([f0ea2a1](https://github.com/danobot/entity-controller/commit/f0ea2a1))



<a name="4.1.6"></a>
## [4.1.6](https://github.com/danobot/entity-controller/compare/v4.1.5...v4.1.6) (2019-12-17)


### Bug Fixes

* rollback implementation for [#98](https://github.com/danobot/entity-controller/issues/98), defective ([66a7a00](https://github.com/danobot/entity-controller/commit/66a7a00))



<a name="4.1.5"></a>
## [4.1.5](https://github.com/danobot/entity-controller/compare/v4.1.4...v4.1.5) (2019-12-17)


### Bug Fixes

* Add state transition for [#98](https://github.com/danobot/entity-controller/issues/98) to ensure requirement 3.2 is fulfilled. ([e0a2a96](https://github.com/danobot/entity-controller/commit/e0a2a96))



<a name="4.1.4"></a>
## [4.1.4](https://github.com/danobot/entity-controller/compare/v4.1.3...v4.1.4) (2019-12-17)



<a name="4.1.3"></a>
## [4.1.3](https://github.com/danobot/entity-controller/compare/v4.1.2...v4.1.3) (2019-12-07)



<a name="4.1.2"></a>
## [4.1.2](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/compare/v4.1.1...v4.1.2) (2019-12-07)



<a name="4.1.1"></a>
## [4.1.1](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/compare/v4.1.0...v4.1.1) (2019-12-06)



<a name="4.1.0"></a>
# [4.1.0](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/compare/v4.0.4...v4.1.0) (2019-10-10)


### Bug Fixes

* pull request template and HACS manifest ([25f0a72](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/commit/25f0a72))


### Features

* hacs ([147cd7f](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/commit/147cd7f))



<a name="4.0.4"></a>
## [4.0.4](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/compare/v4.0.3...v4.0.4) (2019-09-14)



<a name="4.0.3"></a>
## [4.0.3](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/compare/v4.0.2...v4.0.3) (2019-08-13)



<a name="4.0.2"></a>
## [4.0.2](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/compare/v4.0.1...v4.0.2) (2019-08-10)



<a name="4.0.1"></a>
## [4.0.1](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/compare/v4.0.0...v4.0.1) (2019-06-03)


### Bug Fixes

* add manifest.json for HA v0.94 release ([271b237](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/commit/271b237))



<a name="4.0.0"></a>
# [4.0.0](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/compare/v3.3.3...v4.0.0) (2019-05-26)


### Bug Fixes

* Configuration loaded with duplicate entities. Implementation of state entities was erroneous. ([414f6c7](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/commit/414f6c7))


### Features

* Introduce trigger entities whose turn_on service is called when control entities are turned on or off. ([7dc01f6](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/commit/7dc01f6))


### BREAKING CHANGES

* rename entity_on to trigger_on_activate in your configurations!!!

These trigger entities could be scripts that are called whenever control entities are being controlled in some way. For example, when the controller enters active state, control entities are switched on (as usual). At the same time, any defined trigger_on_activate entities will be turned on.



<a name="3.3.3"></a>
## [3.3.3](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/compare/v3.3.2...v3.3.3) (2019-03-20)


### Bug Fixes

* add default delay ([17e3811](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/commit/17e3811)), closes [#47](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/issues/47)
* check state when exiting constrained ([012b94e](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/commit/012b94e)), closes [#43](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/issues/43)
* update readme. closes [#45](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/issues/45) ([0bfed7e](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/commit/0bfed7e))



<a name="3.3.2"></a>
## [3.3.2](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/compare/v3.3.1...v3.3.2) (2019-03-20)



<a name="3.3.1"></a>
## [3.3.1](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/compare/v3.3.0...v3.3.1) (2019-03-11)


### Bug Fixes

* improve debug logging ([1bcccd1](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/commit/1bcccd1))
* **off entities** Array was populated incorrectly on start up.


<a name="3.3.0"></a>
# [3.3.0](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/compare/v3.2.0...v3.3.0) (2019-03-06)


### Bug Fixes

* add True and False to state strings ([52ba126](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/commit/52ba126))
* config validation was not working ([330c4c7](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/commit/330c4c7))

### Features

* Support for custom service data for `turn_off` calls ([#36](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/issues/36)) ([45f50cc](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/commit/45f50cc))
* **duration sensor:** updated config keys, added validations, added `sensor_resets_timer` and updated docs ([d7a8093](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/commit/d7a8093))



<a name="3.2.0"></a>
# [3.2.0](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/compare/v3.1.4...v3.2.0) (2019-03-04)


### Bug Fixes

* add True and False to state strings ([66d0931](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/commit/66d0931))


### Features

* **duration sensor:** updated config keys, added validations, added `sensor_resets_timer` and updated docs ([340e27d](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/commit/340e27d))



<a name="3.1.4"></a>
## [3.1.4](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/compare/v3.1.3...v3.1.4) (2019-03-03)


### Bug Fixes

* revert defective change ([bce14ae](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/commit/bce14ae))



<a name="3.1.3"></a>
## [3.1.3](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/compare/v3.1.2...v3.1.3) (2019-03-03)



<a name="3.1.2"></a>
## [3.1.2](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/compare/v3.1.1...v3.1.2) (2019-03-03)


### Bug Fixes

* Check that the block timer handle is not None before accessing attr. ([#38](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/issues/38)) ([2b36093](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/commit/2b36093))



<a name="3.1.1"></a>
## [3.1.1](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/compare/v3.1.0...v3.1.1) (2019-02-26)


### Bug Fixes

* **blocked mode:** amendment to block timeout restriction. Controller should turn off control entities when blocked mode is exited via block_timer expiry ([f9702f0](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/commit/f9702f0))



<a name="3.1.0"></a>
# [3.1.0](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/compare/v3.0.1...v3.1.0) (2019-02-26)


### Features

* **blocked mode:** add timeout to blocked mode such that the controller takes over after some time. ([9160879](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/commit/9160879))



<a name="3.0.1"></a>
## [3.0.1](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/compare/v3.0.0...v3.0.1) (2019-02-26)


### Bug Fixes

* **tracker:** update component name and location ([91e4950](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/commit/91e4950))



<a name="3.0.0"></a>
# [3.0.0](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/compare/v2.4.10...v3.0.0) (2019-02-26)


### Chores

* rename component, migrate to new directory/file format ([889d5cd](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/commit/889d5cd))


### BREAKING CHANGES

* component has been renamed to entity_controller and migrated to the new file/directory format. To update your configuration, hard-replace `lightingsm` with `entity_controller` in your configuration files and Lovelace config. The directory/file format change may require you go into your `custom_components` folder and manually remove the `lightingsm.py` file and create the new directory structure.



<a name="2.4.10"></a>
## [2.4.10](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/compare/v2.4.9...v2.4.10) (2019-02-11)


### Bug Fixes

* **overrides:** Entity does not go into override mode when override entities are active at start_time. ([ae4cff7](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/commit/ae4cff7))



<a name="2.4.9"></a>
## [2.4.9](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/compare/v2.4.8...v2.4.9) (2019-01-17)



<a name="2.4.8"></a>
## [2.4.8](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/compare/v2.4.7...v2.4.8) (2019-01-17)


### Bug Fixes

* **constraints:** all the things wrong with it. (losing hope) ([4682b1d](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/commit/4682b1d))



<a name="2.4.7"></a>
## [2.4.7](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/compare/v2.4.6...v2.4.7) (2019-01-16)


### Bug Fixes

* **constraints:** sunrise returning yesterdays sunrise. Patches futurize to correct symptom. Better fix required. ([ca3c0ea](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/commit/ca3c0ea))



<a name="2.4.6"></a>
## [2.4.6](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/compare/v2.4.5...v2.4.6) (2019-01-16)



<a name="2.4.5"></a>
## [2.4.5](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/compare/v2.4.4...v2.4.5) (2019-01-16)



<a name="2.4.4"></a>
## [2.4.4](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/compare/v2.4.3...v2.4.4) (2019-01-16)


### Bug Fixes

* **constraints:** first start/stop times are set correctly. Subsequent start/stop time parameters to be tested. ([b67541f](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/commit/b67541f))



<a name="2.4.3"></a>
## [2.4.3](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/compare/v2.4.2...v2.4.3) (2019-01-15)


### Bug Fixes

* **constraints:** End constraint should be adjusted based on current time (does not come after start time if within active period) ([61f7dc1](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/commit/61f7dc1))



<a name="2.4.2"></a>
## [2.4.2](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/compare/v2.4.1...v2.4.2) (2019-01-15)


### Bug Fixes

* **constrains:** Constrains are not observed. Fixes [#20](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/issues/20) ([b9245f0](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/commit/b9245f0))



<a name="2.4.1"></a>
## [2.4.1](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/compare/v2.4.0...v2.4.1) (2019-01-14)



<a name="2.4.0"></a>
# [2.4.0](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/compare/v2.3.0...v2.4.0) (2019-01-14)


### Bug Fixes

* **config:** make override config plural insensitive ([db5ac63](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/commit/db5ac63))
* **constrains:** sunset/sunrise callbacks would not fire ([673250f](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/commit/673250f))
* **constraints:** Some edge case defect fixes ([9af3def](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/commit/9af3def))


### Features

* **constraints:** Add sunset / sunrise expressions to night_mode ([1bc74e6](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/commit/1bc74e6))



<a name="2.3.0"></a>
# [2.3.0](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/compare/v2.2.10...v2.3.0) (2019-01-14)


### Bug Fixes

* **constrains:** Catch TypeError when times start with number. Fixes [#17](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/issues/17). ([beef4f5](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/commit/beef4f5))
* **constrains:** fixes [#15](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/issues/15) constrain end callback and start callback mixed up ([668b375](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/commit/668b375))
* **test:** entity id already exists ([6646b41](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/commit/6646b41))
* accept time offset with quotes ([98201f0](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/commit/98201f0))
* callback parameters ([7d559b0](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/commit/7d559b0))
* idle icon to outline circle ([fb49916](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/commit/fb49916))
* sun component returns UTC time. convert to local time ([c17179e](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/commit/c17179e))


### Features

* **constraints:** Add support for sunset and sunrise expressions ([e9ed0b2](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/commit/e9ed0b2))
* **constraints:** Add support for sunset and sunrise expressions ([91f80f3](https://gitlab.danielha.tk/HA/appdaemon-motion-lights/commit/91f80f3))


# Old Changelog
v0.1.0      First formal Release
v0.2.0      Added customizable state strings, fixes defect
v0.3.0      Add override switch functionality
v0.4.0      Add entities and state_entities configuration (experimental)

v1.0.0      Major rewrite using state machine implementation and more configuration options
v1.0.1      Fix typos in readme, update module reference in test suite
v1.1.0      Implements Home Assistant state entities including state attributes
v1.1.1      Add more information to state attributes

v2.0.0      HA component rewrite
v2.1.0      Implement time constraints and entity icons
v2.2.0      State attributes and defects
v2.2.1      Defect state entity
v2.2.2      Defect constrain times
v2.2.3      Defects: allow transitions in constrained state and lights would not turn off defect
v2.2.4      sensor duration type defect
v2.2.5      override config testing, backoff testing completed
v2.2.6      observe state entities (not control entities), fix function call typo, go to idle when all state entities switched off while active.
v2.2.7      night mode to activate on startup, add mode state attribute
v2.2.8      Error fix: calling entity update before Entity is added to hass
v2.2.9      Improved trigger and event handling, added blocked_by and blocked_at state attributes
v2.2.10     Defect fix #9, #12
v2.3.0      Feature: Sunset/sunrise support in start_time and end_time