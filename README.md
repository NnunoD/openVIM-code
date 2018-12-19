# openVIM-code

**Last update:** 2018-12-19, Nuno Domingues<br/>
**Description:** Changes made to OpenVIM in order to instantiate VM/servers in ARM processors.<br/>
Copy code on create_xml_server.py and substitute the respective OpenVIM function on:<br/>
* file: _(openvim_directory)/osm_openvim/host_thread.py_<br/>
* function: _create_xml_server_<br/><br/>

**Notes:**
- OpenVIM installed on Ubuntu 16.04 (x86_64)
- VMs instantiated on Raspberry Pi 3 Model B with openSUSE 42.3 (arm64)
- Images tested: Debian Official Cloud Images for OpenStack (arm64 images, specifically Debian 9.5.0)

