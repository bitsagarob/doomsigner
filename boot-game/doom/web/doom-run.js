/*
 * DoomRun: the page's one handle on the DOOM build.
 *
 *   DoomRun.start({ wadUrl, onFrame })   onFrame(Uint8Array) once per frame
 *   DoomRun.key(name, isDown)            one of the eight buttons on the device
 *   DoomRun.stop()
 *   DoomRun.ready                        resolves once DOOM is running
 *
 * onFrame is handed one panel's worth of RGB565, big endian: byte for byte what
 * the ST7789 on a real SeedSigner receives over SPI, letterboxed the same way,
 * because it comes out of the same scaler the device firmware uses. Not DOOM
 * rendered nicely for a canvas, which would look better and be a lie.
 *
 * This file is the small half, and it is deliberately the only half the page
 * loads up front. The engine (doom.js, and the doom.wasm it pulls in) and the
 * WAD are fetched by start() and by nothing else, so a visitor who asked for
 * the wallet never pays for a game that is not going to run. doom.js is looked
 * for next to this file rather than relative to the page, so both can be served
 * from wherever the page's assets live without anyone passing paths around.
 */
(function (global) {
    'use strict';

    /*
     * Where the WAD is written inside the module's virtual filesystem. Nothing
     * outside this file knows the name, and DOOM only ever opens the one file.
     */
    var WAD_PATH = '/doom.wad';

    /*
     * Button ids, matching the enum at the top of src/dg_wasm.c. Names are the
     * panel's rather than DOOM's, because the caller is describing hardware it
     * is drawing, not a keyboard.
     */
    var BUTTONS = {
        up: 0, down: 1, left: 2, right: 3, select: 4,
        key1: 5, key2: 6, key3: 7,
    };

    /*
     * Read now, while this script is the one executing, because that is the
     * only moment currentScript answers.
     */
    var here = (typeof document !== 'undefined' && document.currentScript)
        ? document.currentScript.src.replace(/[^/]*$/, '')
        : '';

    var doom = null;
    var settle = {};

    /*
     * Created now rather than in start(), so a page can hold onto DoomRun.ready
     * before it has decided to start anything.
     */
    var ready = new Promise(function (resolve, reject) {
        settle.resolve = resolve;
        settle.reject = reject;
    });

    /*
     * doom.js defines createDoomModule and finds doom.wasm next to itself. A
     * caller that has already put the factory in place, which is how the tests
     * run this under node, is left alone.
     */
    function loadEngine() {
        if (global.createDoomModule) {
            return Promise.resolve(global.createDoomModule);
        }

        return new Promise(function (resolve, reject) {
            var script = document.createElement('script');
            script.src = here + 'doom.js';
            script.onload = function () {
                if (global.createDoomModule) {
                    resolve(global.createDoomModule);
                } else {
                    reject(new Error('doom.js defined no module'));
                }
            };
            script.onerror = function () {
                reject(new Error('cannot load ' + script.src));
            };
            document.head.appendChild(script);
        });
    }

    function fetchWad(wadUrl) {
        return fetch(wadUrl).then(function (response) {
            if (!response.ok) {
                throw new Error('WAD fetch failed: ' + response.status + ' ' + wadUrl);
            }
            return response.arrayBuffer();
        });
    }

    function start(options) {
        var onFrame = options.onFrame;

        /* Both are wanted before anything can begin, so ask for both at once. */
        Promise.all([loadEngine(), fetchWad(options.wadUrl)]).then(function (parts) {
            var factory = parts[0];
            var wad = parts[1];

            return factory({
                /*
                 * The frame arrives as a view straight into the wasm heap and
                 * stops being valid at the next one. Copying it here, once,
                 * rather than making every caller remember that: 115KB thirty
                 * five times a second is nothing next to the bug it prevents.
                 */
                onDoomFrame: function (view) {
                    onFrame(new Uint8Array(view));
                },
            }).then(function (loaded) {
                loaded.FS.writeFile(WAD_PATH, new Uint8Array(wad));
                return loaded;
            });
        }).then(function (loaded) {
            /*
             * This blocks while DOOM reads the WAD and builds its zone, a
             * second or two, and returns once the main loop is scheduled. So
             * resolving after it means what it says: DOOM is running.
             */
            loaded.ccall('ss_doom_start', null, ['string'], [WAD_PATH]);
            doom = loaded;
            settle.resolve();
        }).catch(function (error) {
            settle.reject(error);
        });

        return ready;
    }

    /*
     * Returns true if the button drove the game and false if it was left alone.
     * KEY1, KEY2 and KEY3 always return false: they spell the unlock, they are
     * the caller's to interpret, and nothing here consumes them or turns them
     * into a game action. An unknown name throws, so a typo cannot pass for a
     * button that simply did nothing.
     */
    function key(name, isDown) {
        var button = BUTTONS[name];
        if (button === undefined) {
            throw new Error('unknown button: ' + name);
        }
        if (!doom) {
            return false;
        }

        return doom.ccall('ss_doom_button', 'number',
                          ['number', 'number'], [button, isDown ? 1 : 0]) === 1;
    }

    function stop() {
        if (doom) {
            doom.ccall('ss_doom_stop', null, [], []);
        }
    }

    global.DoomRun = {
        start: start,
        key: key,
        stop: stop,
        ready: ready,

        /*
         * The emscripten module underneath, null until it is running. Nothing
         * in the page should need it; it is here so a test can read DOOM's own
         * input queue rather than guess at it from the picture.
         */
        get module() { return doom; },
    };

    if (typeof module !== 'undefined' && module.exports) {
        module.exports = global.DoomRun;
    }
})(typeof globalThis !== 'undefined' ? globalThis : this);
