$(function() {

    function ProbeTramViewModel(parameters) {
        var self = this;

        self.settings = parameters[0];
        self.printerState = parameters[1];
        self.printerConnection = parameters[2];

        self.setUIEnabled = function (enabled) {
            document.querySelectorAll(".control-button").forEach( elem => {
                elem.disabled = !enabled;
            })
        }

        self.probeAll = function() {
            OctoPrint.simpleApiCommand('probetram', 'probe_all');
        }

        self.probePoint = function(point) {
            OctoPrint.simpleApiCommand('probetram', 'probe_point', {"point": point});
        }

        self.onEventplugin_probetram_ui_availability_change = function (payload) {
            self.setUIEnabled(payload["available"])
        }


        /* Event handler for the custom event "probe_complete". */
        self.onEventplugin_probetram_probe_complete = function(payload) {


            let point = payload["point"]
            let zValue = payload["z"]
            let is_batch = payload["isBatch"]
            let is_batch_tail = payload["isBatchTail"]

            document.getElementById("z-value-p"+point).textContent = zValue;

            if(!is_batch){
                self.resetAllResultStyles("invalid");
                document.getElementById("result-"+point).class = "result point-box-child latest";
            }

        }

        self.resetAllResultStyles = function(suffix) {
            for(let i = 0; i < 5; i++){
                document.getElementById("result-"+i).class = "result point-box-child " + suffix;
            }
        }

        // Assign relevant probePoint() function to each probe button
        for(let i = 0; i < 5; i++){
            document.getElementById("probe-" + i + "-btn").addEventListener("click", function (){
                self.probePoint(i);
            })
        }

        document.getElementById("probetram-settings-button").addEventListener("click", function(){
            self.settings.show('#settings_plugin_probetram');
        })

        self.setUIEnabled(false);

        self.clearAll = function(){
            for(let i = 0; i < 5; i++){
                document.getElementById("z-value-p"+i).textContent = "?";
            }
            self.resetAllResultStyles("");
        }

        self.onBeforeBinding = function () {
            OctoPrint.connection.getSettings().then(result => {
                self.setUIEnabled(result["current"]["state"] === "Operational");
            });
        }

    }

    // This is how our plugin registers itself with the application, by adding some configuration
    // information to the global variable OCTOPRINT_VIEWMODELS
    OCTOPRINT_VIEWMODELS.push({
        construct: ProbeTramViewModel,
        dependencies: ["settingsViewModel", "printerStateViewModel", "connectionViewModel"],
        elements: ["#tab_plugin_probetram"]
    });

})
