/*
 * Runs the browser build headless, in node, and checks that it draws.
 *
 * "It compiles" is not the claim being made. This loads the same doom.js and
 * the same doom-run.js the page loads, feeds them the same WAD, and looks at
 * the bytes that come back out of onFrame:
 *
 *   * every frame is 240*240*2 = 115200 bytes;
 *   * the frames change, so this is a running game and not one still picture;
 *   * frame 0 is written as a PPM in the byte-for-byte format dg_headless
 *     writes, so the two targets can be compared with cmp(1);
 *   * KEY1, KEY2 and KEY3 put nothing at all into DOOM's input queue, which is
 *     read directly rather than inferred from the picture.
 *
 * The only thing faked here is fetch(), because node has no notion of fetching
 * a file off disk and the wrapper is not going to grow a node code path for the
 * sake of its own test.
 *
 *   node tests/run_wasm_frames.js [frame-count] [output-dir]
 */
'use strict';

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const FRAME_BYTES = 240 * 240 * 2;

const root = path.resolve(__dirname, '..');
const frameCount = Number(process.argv[2] || 120);
const outDir = process.argv[3] || path.join(root, 'frames-wasm');
const wadPath = path.join(root, 'wad', 'freedoom1.wad');

fs.mkdirSync(outDir, { recursive: true });

/* The wrapper only ever fetches the WAD, so answering with the file is enough. */
globalThis.fetch = async function (url) {
    const bytes = fs.readFileSync(url);
    return {
        ok: true,
        status: 200,
        arrayBuffer: async () => bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.length),
    };
};

globalThis.createDoomModule = require(path.join(root, 'build', 'doom.js'));
const DoomRun = require(path.join(root, 'web', 'doom-run.js'));

/*
 * The same expansion dg_headless writes, so a PPM from either target is the
 * same file when the pixels are the same. Big endian in, five and six bit
 * fields shifted back up to eight.
 */
function writePpm(file, wire) {
    const header = Buffer.from(`P6\n240 240\n255\n`, 'ascii');
    const body = Buffer.alloc(240 * 240 * 3);

    for (let i = 0; i < 240 * 240; i++) {
        const pixel = (wire[i * 2] << 8) | wire[i * 2 + 1];
        body[i * 3] = ((pixel >> 11) & 0x1f) << 3;
        body[i * 3 + 1] = ((pixel >> 5) & 0x3f) << 2;
        body[i * 3 + 2] = (pixel & 0x1f) << 3;
    }

    fs.writeFileSync(file, Buffer.concat([header, body]));
}

/*
 * A player standing still is a poor test: the only thing that moves is the
 * animated flats, so most frames repeat and "the frames change" proves little.
 * Walk and turn instead, which is also what a visitor will do. {frame, button,
 * isDown}, applied in order.
 */
const script = [
    [10, 'up', true], [40, 'up', false],
    [45, 'right', true], [60, 'right', false],
    [65, 'up', true], [95, 'up', false],
    [100, 'select', true], [103, 'select', false],
];
let scriptIndex = 0;

const digests = [];
let wrongSize = 0;
let done = false;

function onFrame(bytes) {
    if (done) {
        return;
    }
    if (bytes.length !== FRAME_BYTES) {
        wrongSize++;
    }

    const index = digests.length;
    while (scriptIndex < script.length && script[scriptIndex][0] <= index) {
        const step = script[scriptIndex++];
        DoomRun.key(step[1], step[2]);
    }

    digests.push(crypto.createHash('sha256').update(bytes).digest('hex'));

    if (index === 0 || index === Math.floor(frameCount / 2) || index === frameCount - 1) {
        writePpm(path.join(outDir, `wasm-${String(index).padStart(4, '0')}.ppm`), bytes);
    }

    if (digests.length >= frameCount) {
        done = true;
        finish();
    }
}

function pending() {
    return DoomRun.module.ccall('ss_doom_pending', 'number', [], []);
}

/*
 * Each press is measured against DOOM's own input queue, read straight after
 * the call. The main loop is already cancelled by the time this runs, so
 * nothing drains the queue underneath the measurement.
 */
function keyReport() {
    const rows = [];
    for (const name of ['up', 'down', 'left', 'right', 'select', 'key1', 'key2', 'key3']) {
        const before = pending();
        const consumed = DoomRun.key(name, true);
        rows.push({ name, consumed, queuedOnPress: pending() - before });
        DoomRun.key(name, false);
    }
    return rows;
}

function finish() {
    DoomRun.stop();

    const unique = new Set(digests);
    const consecutiveChanges = digests.filter((d, i) => i > 0 && d !== digests[i - 1]).length;

    console.log('');
    console.log(`frames captured      ${digests.length}`);
    console.log(`bytes per frame      ${FRAME_BYTES} (wrong-sized frames: ${wrongSize})`);
    console.log(`distinct frames      ${unique.size}`);
    console.log(`frame != previous    ${consecutiveChanges} of ${digests.length - 1}`);
    console.log(`first frame sha256   ${digests[0]}`);
    console.log(`last frame sha256    ${digests[digests.length - 1]}`);
    console.log(`ppm written to       ${outDir}`);
    console.log('');
    console.log('button               consumed by DOOM   keys queued on press');
    const keys = keyReport();
    for (const row of keys) {
        console.log(`  ${row.name.padEnd(19)}${String(row.consumed).padEnd(19)}${row.queuedOnPress}`);
    }

    const reserved = keys.filter((row) => row.name.startsWith('key'));
    const reservedClean = reserved.every((row) => row.consumed === false && row.queuedOnPress === 0);
    const gameButtons = keys.filter((row) => !row.name.startsWith('key'));
    const gameWired = gameButtons.every((row) => row.consumed === true && row.queuedOnPress > 0);

    const ok = wrongSize === 0 && unique.size > 1 && digests.length === frameCount
        && reservedClean && gameWired;
    console.log('');
    console.log(ok ? 'PASS' : 'FAIL');
    process.exit(ok ? 0 : 1);
}

DoomRun.start({ wadUrl: wadPath, onFrame: onFrame });

DoomRun.ready.then(function () {
    console.log('doom is running');
}).catch(function (error) {
    console.error('start failed:', error);
    process.exit(1);
});
