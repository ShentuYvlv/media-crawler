#!/usr/bin/env node

const fs = require('fs');
const { generateRequestUrl, ROUTES } = require('./Hkey.js');
const localAuth = require('./local_auth.js');

function parseArgs(argv) {
    const args = argv.slice(2);
    if (args.length === 0 || args.includes('--help') || args.includes('-h')) {
        return { help: true };
    }

    if (args.includes('--list') || args.includes('-l')) {
        return { list: true };
    }

    const routeName = args[0];
    const customParams = {};

    for (let i = 1; i < args.length; i++) {
        const arg = args[i];
        if (!arg.includes('=')) {
            continue;
        }
        const [key, ...rest] = arg.split('=');
        customParams[key] = rest.join('=');
    }

    return { help: false, list: false, routeName, customParams };
}

function parseStdinJson() {
    const raw = fs.readFileSync(0, 'utf8').trim();
    if (!raw) {
        return null;
    }

    const parsed = JSON.parse(raw);
    return {
        routeName: parsed.routeName,
        customParams: parsed.customParams || {}
    };
}

function getRuntimeConfig() {
    const headers = {
        accept: 'application/json, text/plain, */*',
        origin: localAuth.origin || 'https://www.xiaoheihe.cn',
        referer: localAuth.referer || 'https://www.xiaoheihe.cn/',
        'user-agent': localAuth.userAgent || 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36'
    };

    if (localAuth.cookie) {
        headers.cookie = localAuth.cookie;
    }

    return {
        headers,
        baseOverrides: {
            heybox_id: localAuth.heyboxId || '',
            x_os_type: localAuth.xOsType || 'Windows',
            device_info: localAuth.deviceInfo || 'Chrome',
            device_id: localAuth.deviceId || '2c2fef8385ccef915e3b3caf94e3aa06'
        }
    };
}

function main() {
    if (process.argv.includes('--stdin-json')) {
        const parsed = parseStdinJson();

        if (!parsed || !parsed.routeName) {
            console.error(JSON.stringify({
                ok: false,
                error: 'missing routeName in stdin json'
            }));
            process.exit(1);
            return;
        }

        if (!ROUTES[parsed.routeName]) {
            console.error(JSON.stringify({
                ok: false,
                error: `unknown route: ${parsed.routeName}`,
                routes: Object.keys(ROUTES)
            }));
            process.exit(1);
            return;
        }

        try {
            const runtimeConfig = getRuntimeConfig();
            const requestInfo = generateRequestUrl(parsed.routeName, parsed.customParams, runtimeConfig.baseOverrides);

            console.log(JSON.stringify({
                ok: true,
                route: parsed.routeName,
                path: requestInfo.path,
                hkey: requestInfo.hkey,
                timestamp: requestInfo.timestamp,
                nonce: requestInfo.nonce,
                url: requestInfo.url,
                headers: runtimeConfig.headers,
                params: parsed.customParams
            }, null, 2));
            return;
        } catch (error) {
            console.error(JSON.stringify({
                ok: false,
                error: error.message
            }));
            process.exit(1);
            return;
        }
    }

    const parsed = parseArgs(process.argv);

    if (parsed.help) {
        console.log(JSON.stringify({
            ok: true,
            usage: 'node generate_request_json.js <route> [key=value params]',
            routes: Object.keys(ROUTES)
        }, null, 2));
        return;
    }

    if (parsed.list) {
        console.log(JSON.stringify({
            ok: true,
            routes: Object.fromEntries(Object.entries(ROUTES).map(([name, config]) => [name, config.params]))
        }, null, 2));
        return;
    }

    if (!ROUTES[parsed.routeName]) {
        console.error(JSON.stringify({
            ok: false,
            error: `unknown route: ${parsed.routeName}`,
            routes: Object.keys(ROUTES)
        }));
        process.exit(1);
        return;
    }

    try {
        const runtimeConfig = getRuntimeConfig();
        const requestInfo = generateRequestUrl(parsed.routeName, parsed.customParams, runtimeConfig.baseOverrides);

        console.log(JSON.stringify({
            ok: true,
            route: parsed.routeName,
            path: requestInfo.path,
            hkey: requestInfo.hkey,
            timestamp: requestInfo.timestamp,
            nonce: requestInfo.nonce,
            url: requestInfo.url,
            headers: runtimeConfig.headers,
            params: parsed.customParams
        }, null, 2));
    } catch (error) {
        console.error(JSON.stringify({
            ok: false,
            error: error.message
        }));
        process.exit(1);
    }
}

main();
