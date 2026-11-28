"""Isolated authenticated delivery tests; no real key, network, or third-party JAR."""
import hashlib
import io
import json
import os
import unittest
import urllib.request
import zipfile
from unittest.mock import Mock, patch
from scripts import probe_dragonrise_delivery as probe

URL = "https://edge.forgecdn.net/files/9208/25/" + probe.NAME
KEY = "synthetic-test-key"

class Response(io.BytesIO):
    def geturl(self):
        return URL

class CDNAuthTests(unittest.TestCase):
    def test_authenticated_api_and_cdn_with_exact_hash(self):
        jar = io.BytesIO()
        with zipfile.ZipFile(jar, "w") as z:
            z.writestr("META-INF/neoforge.mods.toml", "fixture")
            z.writestr("fixture.bin", b"x" * 2048)
        data = jar.getvalue()
        api = Mock()
        cdn = Mock()
        records = [
            {"id":probe.PROJECT,"allowModDistribution":True},
            {"id":probe.FILE,"modId":probe.PROJECT,"fileName":probe.NAME,
             "gameVersions":["1.21.1","NeoForge"],
             "dependencies":[{"relationType":3,"modId":1218165}],
             "downloadUrl":URL,"fileLength":len(data)},
            URL,
        ]
        api.open.side_effect = [Response(json.dumps({"data":x}).encode()) for x in records]
        cdn.open.return_value = Response(data)
        with patch.dict(os.environ, {"CURSEFORGE_API_KEY":KEY}), patch.object(probe,"EXPECTED_SHA256",hashlib.sha256(data).hexdigest()), patch.object(probe.urllib.request,"build_opener",side_effect=[api,cdn]), patch("builtins.print") as output:
            probe.probe()
        for call in api.open.call_args_list + cdn.open.call_args_list:
            req = call.args[0]
            self.assertEqual(req.get_header("X-api-key"),KEY)
            self.assertNotIn(KEY,req.full_url)
        self.assertEqual(cdn.open.call_args.args[0].full_url,URL)
        self.assertNotIn(KEY,str(output.call_args_list))
        self.assertIn(hashlib.sha512(data).hexdigest(),str(output.call_args_list))

    def test_denied_permission_stops_before_cdn(self):
        api = Mock()
        api.open.return_value = Response(json.dumps({"data":{"id":probe.PROJECT,"allowModDistribution":False}}).encode())
        with patch.dict(os.environ,{"CURSEFORGE_API_KEY":KEY}), patch.object(probe.urllib.request,"build_opener",return_value=api) as opener:
            with self.assertRaisesRegex(ValueError,"permission"):
                probe.probe()
            self.assertEqual(opener.call_count,1)
            self.assertEqual(api.open.call_count,1)

    def test_untrusted_redirect_rejected_and_allowed_redirect_keeps_header(self):
        req=urllib.request.Request(URL,headers={"x-api-key":KEY})
        handler=probe.CDNRedirect()
        with self.assertRaisesRegex(ValueError,"Untrusted"):
            handler.redirect_request(req,None,302,"",{},"https://example.org/files/9208/25/"+probe.NAME)
        redirected=handler.redirect_request(req,None,302,"",{},URL.replace("edge.","mediafilez."))
        self.assertEqual(redirected.get_header("X-api-key"),KEY)

if __name__ == "__main__":
    unittest.main()
