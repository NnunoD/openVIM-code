    def create_xml_server(self, server, dev_list, server_metadata={}):
        """Function that implements the generation of the VM XML definition.
        Additional devices are in dev_list list
        The main disk is upon dev_list[0]"""
        
    #get if operating system is Windows        
        windows_os = False
        os_type = server_metadata.get('os_type', None)
        if os_type == None and 'metadata' in dev_list[0]:
            os_type = dev_list[0]['metadata'].get('os_type', None)
        if os_type != None and os_type.lower() == "windows":
            windows_os = True
    #get type of hard disk bus  
        bus_ide = True if windows_os else False   
        bus = server_metadata.get('bus', None)
        if bus == None and 'metadata' in dev_list[0]:
            bus = dev_list[0]['metadata'].get('bus', None)
        if bus != None:
            bus_ide = True if bus=='ide' else False
            
        self.xml_level = 0

        text = "<domain type='kvm'>"
    #get topology
        topo = server_metadata.get('topology', None)
        if topo == None and 'metadata' in dev_list[0]:
            topo = dev_list[0]['metadata'].get('topology', None)
    #name
        name = server.get('name', '')[:28] + "_" + server['uuid'][:28] #qemu impose a length  limit of 59 chars or not start. Using 58
        text += self.inc_tab() + "<name>" + name+ "</name>"
    #uuid
        text += self.tab() + "<uuid>" + server['uuid'] + "</uuid>" 
        
        numa={}
        if 'extended' in server and server['extended']!=None and 'numas' in server['extended']:
            numa = server['extended']['numas'][0]
    #memory
        use_huge = False
        memory = int(numa.get('memory',0))*1024*1024 #in KiB
        if memory==0:
            memory = int(server['ram'])*1024;
        else:
            if not self.develop_mode:
                use_huge = True
        if memory==0:
            return -1, 'No memory assigned to instance'
        memory = str(memory/4)
        text += self.tab() + "<memory unit='KiB'>" +memory+"</memory>" 
        text += self.tab() + "<currentMemory unit='KiB'>" +memory+ "</currentMemory>"
        if use_huge and 1 == 0: # retirar hugepages por enquanto (N)
            text += self.tab()+'<memoryBacking>'+ \
                self.inc_tab() + '<hugepages/>'+ \
                self.dec_tab()+ '</memoryBacking>'

    #cpu
        use_cpu_pinning=False
        vcpus = int(server.get("vcpus",0))
        cpu_pinning = []
        if 'cores-source' in numa:
            use_cpu_pinning=True
            for index in range(0, len(numa['cores-source'])):
                cpu_pinning.append( [ numa['cores-id'][index], numa['cores-source'][index] ] )
                vcpus += 1
        if 'threads-source' in numa:
            use_cpu_pinning=True
            for index in range(0, len(numa['threads-source'])):
                cpu_pinning.append( [ numa['threads-id'][index], numa['threads-source'][index] ] )
                vcpus += 1
        if 'paired-threads-source' in numa:
            use_cpu_pinning=True
            for index in range(0, len(numa['paired-threads-source'])):
                cpu_pinning.append( [numa['paired-threads-id'][index][0], numa['paired-threads-source'][index][0] ] )
                cpu_pinning.append( [numa['paired-threads-id'][index][1], numa['paired-threads-source'][index][1] ] )
                vcpus += 2
        
        if use_cpu_pinning and not self.develop_mode:
            text += self.tab()+"<vcpu placement='static'>" +str(len(cpu_pinning)) +"</vcpu>" + \
                self.tab()+'<cputune>'
            self.xml_level += 1
            for i in range(0, len(cpu_pinning)):
                text += self.tab() + "<vcpupin vcpu='" +str(cpu_pinning[i][0])+ "' cpuset='" +str(cpu_pinning[i][1]) +"'/>"
            text += self.dec_tab()+'</cputune>'+ \
                self.tab() + '<numatune>' +\
                self.inc_tab() + "<memory mode='strict' nodeset='" +str(numa['source'])+ "'/>" +\
                self.dec_tab() + '</numatune>'
        else:
            if vcpus==0:
                return -1, "Instance without number of cpus"
            text += self.tab()+"<vcpu>" + str(vcpus)  + "</vcpu>"

    #boot
        boot_cdrom = False
        for dev in dev_list:
            if dev['type']=='cdrom' :
                boot_cdrom = True
                break
        text += self.tab()+ '<os>' + \
            self.inc_tab() + "<type arch='aarch64' machine='virt-2.9'>hvm</type>"
        if boot_cdrom:
        	text +=  self.tab() + "<boot dev='cdrom'/>" 
        text +=  self.tab() + "<boot dev='hd'/>"
        text +=  self.tab() + "<loader readonly='yes' type='pflash'>/usr/share/qemu/aavmf-aarch64-code.bin</loader>" + \
		self.tab() + "<nvram>/var/lib/libvirt/qemu/nvram/debian_VARS.fd</nvram>" + \
			self.dec_tab()+'</os>'
    #features
        text += self.tab()+'<features>'+\
            self.inc_tab()+'<acpi/>' +\
            self.tab()+'<apic/>' +\
            self.tab()+'<pae/>'+ \
            self.dec_tab() +'</features>'
        if topo == "oneSocket:hyperthreading":
            if vcpus % 2 != 0:
                return -1, 'Cannot expose hyperthreading with an odd number of vcpus'
            text += self.tab() + "<cpu mode='host-model'> <topology sockets='1' cores='%d' threads='2' /> </cpu>" % (vcpus/2)
        elif windows_os or topo == "oneSocket":
            text += self.tab() + "<cpu mode='host-model'> <topology sockets='1' cores='%d' threads='1' /> </cpu>" % vcpus
        else:
            text += self.tab() + "<cpu mode='host-passthrough'>" +\
            	self.inc_tab() + "<model fallback='allow'/>" +\
            	self.dec_tab() + "</cpu>"
        text += self.tab() + "<clock offset='utc'/>" +\
            self.tab() + "<on_poweroff>preserve</on_poweroff>" + \
            self.tab() + "<on_reboot>restart</on_reboot>" + \
            self.tab() + "<on_crash>restart</on_crash>"
        text += self.tab() + "<devices>" + \
            self.inc_tab() + "<emulator>/usr/bin/qemu-system-aarch64</emulator>" + \
            self.tab() + "<serial type='pty'>" +\
            self.inc_tab() + "<target port='0'/>" + \
            self.dec_tab() + "</serial>" +\
            self.tab() + "<console type='pty'>" + \
            self.inc_tab()+ "<target type='serial' port='0'/>" + \
            self.dec_tab()+'</console>'
        if windows_os:
            text += self.tab() + "<controller type='usb' index='0'/>" + \
                self.tab() + "<controller type='ide' index='0'/>" + \
                self.tab() + "<input type='mouse' bus='ps2'/>" + \
                self.tab() + "<sound model='ich6'/>" + \
                self.tab() + "<video>" + \
                self.inc_tab() + "<model type='cirrus' vram='9216' heads='1'/>" + \
                self.dec_tab() + "</video>" + \
                self.tab() + "<memballoon model='virtio'/>" + \
                self.tab() + "<input type='tablet' bus='usb'/>" #TODO revisar

#>             self.tab()+'<alias name=\'hostdev0\'/>\n' +\
#>             self.dec_tab()+'</hostdev>\n' +\
#>             self.tab()+'<input type=\'tablet\' bus=\'usb\'/>\n'
        if windows_os:
            text += self.tab() + "<graphics type='vnc' port='-1' autoport='yes'/>"
        else:
            #If image contains 'GRAPH' include graphics
            #if 'GRAPH' in image:
            #text += self.tab() + "<graphics type='vnc' port='-1' autoport='yes' listen='0.0.0.0'>" +\
            #    self.inc_tab() + "<listen type='address' address='0.0.0.0'/>" +\
            #    self.dec_tab() + "</graphics>"
            text += self.tab() + "<video>" +\
            	self.inc_tab() + "<model type='virtio'/>" +\
            	self.dec_tab() + "</video>"

        vd_index = 'a'
        for dev in dev_list:
            bus_ide_dev = bus_ide
            if dev['type']=='cdrom' or dev['type']=='disk':
                if dev['type']=='cdrom':
                    bus_ide_dev = True
                text += self.tab() + "<disk type='file' device='"+dev['type']+"'>"
                if 'file format' in dev:
                    text += self.inc_tab() + "<driver name='qemu' type='"  +dev['file format']+ "' cache='writethrough'/>"
                if 'source file' in dev:
                    text += self.tab() + "<source file='" +dev['source file']+ "'/>"
                #elif v['type'] == 'block':
                #    text += self.tab() + "<source dev='" + v['source'] + "'/>"
                #else:
                #    return -1, 'Unknown disk type ' + v['type']
                vpci = dev.get('vpci',None)
                if vpci == None and 'metadata' in dev:
                    vpci = dev['metadata'].get('vpci',None)
                #text += self.pci2xml(vpci)
                #text += self.tab() + "<address type='drive' controller='0' bus='0' target='0' unit='0'/>"
               
                if bus_ide_dev:
                    text += self.tab() + "<target dev='hd" +vd_index+ "' bus='ide'/>"   #TODO allows several type of disks
                else:
                    text += self.tab() + "<target dev='vd" +vd_index+ "' bus='virtio'/>"
                text += self.dec_tab() + '</disk>'
                vd_index = chr(ord(vd_index)+1)
            elif dev['type']=='xml':
                dev_text = dev['xml']
                if 'vpci' in dev:
                    dev_text = dev_text.replace('__vpci__', dev['vpci'])
                if 'source file' in dev:
                    dev_text = dev_text.replace('__file__', dev['source file'])
                if 'file format' in dev:
                    dev_text = dev_text.replace('__format__', dev['source file'])
                if '__dev__' in dev_text:
                    dev_text = dev_text.replace('__dev__', vd_index)
                    vd_index = chr(ord(vd_index)+1)
                text += dev_text
            else:
                return -1, 'Unknown device type ' + dev['type']

        net_nb=0
        bridge_interfaces = server.get('networks', [])
        for v in bridge_interfaces:
            #Get the brifge name
            self.db_lock.acquire()
            result, content = self.db.get_table(FROM='nets', SELECT=('provider',),WHERE={'uuid':v['net_id']} )
            self.db_lock.release()
            if result <= 0:
                self.logger.error("create_xml_server ERROR %d getting nets %s", result, content)
                return -1, content
            #ALF: Allow by the moment the 'default' bridge net because is confortable for provide internet to VM
            #I know it is not secure    
            #for v in sorted(desc['network interfaces'].itervalues()):
            model = v.get("model", None)
            if content[0]['provider']=='default':
                text += self.tab() + "<interface type='network'>" + \
                    self.inc_tab() + "<source network='" +content[0]['provider']+ "'/>"
            elif content[0]['provider'][0:7]=='macvtap':
                text += self.tab()+"<interface type='direct'>" + \
                    self.inc_tab() + "<source dev='" + self.get_local_iface_name(content[0]['provider'][8:]) + "' mode='bridge'/>" + \
                    self.tab() + "<target dev='macvtap0'/>"
                if windows_os:
                    text += self.tab() + "<alias name='net" + str(net_nb) + "'/>"
                elif model==None:
                    model = "virtio"
            elif content[0]['provider'][0:6]=='bridge':
                text += self.tab() + "<interface type='bridge'>" +  \
                    self.inc_tab()+"<source bridge='" +self.get_local_iface_name(content[0]['provider'][7:])+ "'/>"
                if windows_os:
                    text += self.tab() + "<target dev='vnet" + str(net_nb)+ "'/>" +\
                        self.tab() + "<alias name='net" + str(net_nb)+ "'/>"
                elif model==None:
                    model = "virtio"
            elif content[0]['provider'][0:3] == "OVS":
                vlan = content[0]['provider'].replace('OVS:', '')
                text += self.tab() + "<interface type='bridge'>" + \
                        self.inc_tab() + "<source bridge='ovim-" + str(vlan) + "'/>"
            else:
                return -1, 'Unknown Bridge net provider ' + content[0]['provider']
            if model!=None:
                text += self.tab() + "<model type='" +model+ "'/>"
            if v.get('mac_address', None) != None:
                text+= self.tab() +"<mac address='" +v['mac_address']+ "'/>"
            text += self.pci2xml(v.get('vpci',None))
            text += self.tab() + "<rom file=''/>"
            text += self.dec_tab()+'</interface>'
            
            net_nb += 1

        interfaces = numa.get('interfaces', [])

        net_nb=0
        for v in interfaces:
            if self.develop_mode: #map these interfaces to bridges
                text += self.tab() + "<interface type='bridge'>" +  \
                    self.inc_tab()+"<source bridge='" +self.develop_bridge_iface+ "'/>"
                if windows_os:
                    text += self.tab() + "<target dev='vnet" + str(net_nb)+ "'/>" +\
                        self.tab() + "<alias name='net" + str(net_nb)+ "'/>"
                else:
                    text += self.tab() + "<model type='e1000'/>" #e1000 is more probable to be supported than 'virtio'
                if v.get('mac_address', None) != None:
                    text+= self.tab() +"<mac address='" +v['mac_address']+ "'/>"
                text += self.pci2xml(v.get('vpci',None))
                text += self.dec_tab()+'</interface>'
                continue
                
            if v['dedicated'] == 'yes':  #passthrought
                text += self.tab() + "<hostdev mode='subsystem' type='pci' managed='yes'>" + \
                    self.inc_tab() + "<source>"
                self.inc_tab()
                text += self.pci2xml(v['source'])
                text += self.dec_tab()+'</source>'
                text += self.pci2xml(v.get('vpci',None))
                if windows_os:
                    text += self.tab() + "<alias name='hostdev" + str(net_nb) + "'/>"
                text += self.dec_tab()+'</hostdev>'
                net_nb += 1
            else:        #sriov_interfaces
                #skip not connected interfaces
                if v.get("net_id") == None:
                    continue
                text += self.tab() + "<interface type='hostdev' managed='yes'>"
                self.inc_tab()
                if v.get('mac_address', None) != None:
                    text+= self.tab() + "<mac address='" +v['mac_address']+ "'/>"
                text+= self.tab()+'<source>'
                self.inc_tab()
                text += self.pci2xml(v['source'])
                text += self.dec_tab()+'</source>'
                if v.get('vlan',None) != None:
                    text += self.tab() + "<vlan>   <tag id='" + str(v['vlan']) + "'/>   </vlan>"
                text += self.pci2xml(v.get('vpci',None))
                if windows_os:
                    text += self.tab() + "<alias name='hostdev" + str(net_nb) + "'/>"
                text += self.tab() + "<rom file=''/>"
                text += self.dec_tab()+'</interface>'

            
        text += self.dec_tab()+'</devices>'+\
        self.dec_tab()+'</domain>'
        return 0, text
