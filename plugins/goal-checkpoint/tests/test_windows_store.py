import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/windows_store.py'

@unittest.skipUnless(os.name == 'nt', 'Windows only')
class WindowsStoreTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('windows_store',SCRIPT)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.temp = tempfile.TemporaryDirectory(prefix='checkpoint space 日本語 ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def store(self):
        def parse(raw):
            if len(raw)>16384:
                raise ValueError('size')
            return json.loads(raw)
        return self.module.WindowsStore(self.root,error=ValueError,bounded_json=parse)

    def test_unicode_atomic_recovery(self):
        name = 'a'*64+'.state.json'
        with self.store() as store:
            with store.lock('session'):
                store.write(name,{'value':'日本語'})
                store.write(name,{'value':2})
                self.assertEqual(store.read(name),{'value':2})
                (store.directory/name).write_bytes(b'{')
                with self.assertRaises(json.JSONDecodeError):
                    store.write(name,{'value':3})
                store.write(name,{'value':3},recover=True)
                self.assertEqual(store.read(name),{'value':3})
                self.assertEqual(list(store.directory.glob('*.tmp')),[])

    def test_atomic_replace_failure_preserves_old_bytes(self):
        import ctypes
        name = 'e'*64+'.state.json'
        with self.store() as store:
            store.write(name,{'value':'original 日本語'})
            original = (store.directory/name).read_bytes()
            def fail_move(*args):
                ctypes.set_last_error(5)
                return False
            with patch.object(self.module,'move',side_effect=fail_move):
                with self.assertRaises(OSError):
                    store.write(name,{'value':'replacement'})
            self.assertEqual((store.directory/name).read_bytes(),original)
            self.assertEqual(list(store.directory.glob('*.tmp')),[])
            self.assertEqual(store.read(name),{'value':'original 日本語'})

    def test_lock_other_process(self):
        code = "import importlib.util,json,sys; s=importlib.util.spec_from_file_location('w',sys.argv[1]); m=importlib.util.module_from_spec(s); s.loader.exec_module(m)\nwith m.WindowsStore(sys.argv[2],error=ValueError,bounded_json=json.loads) as st:\n with st.lock('session'): pass"
        with self.store() as store, store.lock('session'):
            child = subprocess.run([sys.executable,'-c',code,str(SCRIPT),str(self.root)],capture_output=True,text=True,timeout=15)
            self.assertNotEqual(child.returncode,0)
            self.assertIn('Another event',child.stderr)
        with self.store() as store, store.lock('session'):
            pass

    def test_directory_pinned(self):
        with self.store() as store:
            with self.assertRaises(OSError):
                store.directory.rename(self.root/'swapped')

    def test_hardlink_rejected(self):
        name = 'b'*64+'.state.json'
        with self.store() as store:
            store.write(name,{'ok':True})
            os.link(store.directory/name,store.directory/('c'*64+'.state.json'))
            with self.assertRaisesRegex(ValueError,'Unsafe'):
                store.read(name)
            with self.assertRaisesRegex(ValueError,'Unsafe'):
                store.write(name,{},recover=True)

    def test_world_access_rejected(self):
        import ctypes as c
        module=self.module
        setter=module.bind(module.a,'SetNamedSecurityInfoW',[c.wintypes.LPWSTR,c.wintypes.DWORD,c.wintypes.DWORD,c.c_void_p,c.c_void_p,c.c_void_p,c.c_void_p],c.wintypes.DWORD)
        getter=module.bind(module.a,'GetSecurityDescriptorDacl',[c.c_void_p,c.POINTER(c.wintypes.BOOL),c.POINTER(c.c_void_p),c.POINTER(c.wintypes.BOOL)])
        with self.store() as store:
            name='d'*64+'.state.json'
            store.write(name,{})
            descriptor=c.c_void_p()
            module.checked(module.sddl('D:P(A;;FA;;;WD)',1,c.byref(descriptor),None))
            try:
                present,defaulted,dacl=c.wintypes.BOOL(),c.wintypes.BOOL(),c.c_void_p()
                module.checked(getter(descriptor,c.byref(present),c.byref(dacl),c.byref(defaulted)))
                self.assertEqual(setter(str(store.directory/name),1,0x80000004,None,None,dacl,None),0)
                with self.assertRaisesRegex(ValueError,'another principal'):
                    store.read(name)
                with self.assertRaisesRegex(ValueError,'another principal'):
                    store.write(name,{},recover=True)
            finally:
                module.free(descriptor)

    def test_junction_rejected(self):
        target=self.root/'target'
        target.mkdir()
        linked=self.root/'linked'
        result=subprocess.run(['cmd','/c','mklink','/J',str(linked),str(target)],capture_output=True,timeout=10)
        self.assertEqual(result.returncode,0)
        self.addCleanup(lambda: os.rmdir(linked))
        with self.assertRaisesRegex(ValueError,'Unsafe'):
            with self.module.WindowsStore(linked,error=ValueError,bounded_json=json.loads):
                pass

if __name__ == '__main__':
    unittest.main()
