var map;
var user_data = {};
var inventory = {};
var playerInfo = {};
var pokedex = {};
var bagPokemon = {};
var bagItems = {};
var bagCandy = {};
var emptyDex = [];
var pokemonArray = {};
var forts = [];
var info_windows = [];
var i;
var user_index;
var trainerSex = ["m","f"];
var numTrainers = [177, 109];
var menu;
var stats = {};
var _ITEMS_ = {
    "0": "Unknown",

    "1": "Pokeball",
    "2": "Greatball",
    "3": "Ultraball",
    "4": "Masterball",

    "101": "Potion",
    "102": "Super Potion",
    "103": "Hyper Potion",
    "104": "Max Potion",

    "201": "Revive",
    "202": "Max Revive",

    "301": "Lucky Egg",

    "401": "Incense",
    "402": "Spicy Incense",
    "403": "Cool Incense",
    "404": "Floral Incense",

    "501": "Troy Disk",

    "602": "X Attack",
    "603": "X Defense",
    "604": "X Miracle",

    "701": "Razz Berry",
    "702": "Bluk Berry",
    "703": "Nanab Berry",
    "704": "Wepar Berry",
    "705": "Pinap Berry",

    "801": "Special Camera",

    "901": "Incubator (Unlimited)",
    "902": "Incubator",

    "1001": "Pokemon Storage Upgrade",
    "1002": "Item Storage Upgrade"
}


function initMap() {
  // load pokemon data now..
  loadJSON('pokemondata.json', function(data, successData) {
    console.log('Loaded pokemon data..');
    pokemonArray = data;
  }, errorFunc, 'pokemonData');
  for (var i = 0; i < users.length; i++) {
    user_data[users[i]] = {};
  }
  map = new google.maps.Map(document.getElementById('map'), {
    center: {lat: 50.0830986, lng: 6.7613762},
    zoom: 8
  });
  document.getElementById("switchPan").checked = userFollow;
  document.getElementById("switchZoom").checked = userZoom;
  document.getElementById("imageType").checked = false;
  setTimeout(function(){
    placeTrainer();
    addCatchable();
    // updateInventory();
    setTimeout(function(){
      setInterval(updateTrainer, 1000);
      setInterval(addCatchable, 1000);
    }, 5000);
  }, 5000);
};

$('#switchPan').change(function(){
    if (this.checked) { userFollow = true } else { userFollow = false; }
});

$('#switchZoom').change(function(){
    if (this.checked) { userZoom = true } else { userZoom = false; }
});

$('#imageType').change(function(){
    if (this.checked) { imageExt = ".gif" } else { imageExt = ".png"; }
});

$('#tInfo').click(function(){
    if (menu == undefined || menu == 1) {
      $("#submenu").toggle();
    }
    if (menu != 1 && $("#submenu").is(':hidden')) {
      $("#submenu").toggle();
    }
    menu = 1;
    buildMenu();
});

$('#tItems').click(function(){
    if (menu == undefined || menu == 2) {
      $("#submenu").toggle();
    }
    if (menu != 2 && $("#submenu").is(':hidden')) {
      $("#submenu").toggle();
    }
    menu = 2;
    buildMenu();
});

$('#tPokemon').click(function(){
    if (menu == undefined || menu == 3) {
      $("#submenu").toggle();
    }
    if (menu != 3 && $("#submenu").is(':hidden')) {
      $("#submenu").toggle();
    }
    menu = 3;
    buildMenu();
});

$('#tPokedex').click(function(){
    if (menu == undefined || menu == 4) {
      $("#submenu").toggle();
    }
    if (menu != 4 && $("#submenu").is(':hidden')) {
      $("#submenu").toggle();
    }
    menu = 4;
    buildMenu();
});


var errorFunc = function(xhr) {
  console.error(xhr);
};

var invSuccess = function(data, user_index) {
  stats = filter(data, 'player_stats');
  bagItems = filter(data, 'item')
  bagPokemon = filter(data, 'pokemon_data');
  pokedex = filter(data, 'pokedex_entry');
  bagCandy = filter(data, 'pokemon_family')
}

var trainerFunc = function(data, user_index) {
  for (var i = 0; i < data.cells.length; i++) {
    cell = data.cells[i];
    if (data.cells[i].forts != undefined) {
      for (var x = 0; x < data.cells[i].forts.length; x++) {
        var fort = cell.forts[x];
        if (!forts[fort.id]) {
          if (fort.type === 1 ) {
            forts[fort.id] = new google.maps.Marker({
              map: map,
              position: {
                lat: parseFloat(fort.latitude),
                lng: parseFloat(fort.longitude)
              },
              icon: "image/forts/Pstop.png"
            });
          } else {
            forts[fort.id] = new google.maps.Marker({
              map: map,
              position: {
                lat: parseFloat(fort.latitude),
                lng: parseFloat(fort.longitude)
              },
              icon: "image/forts/Gym.png"
            });
          }
          var contentString = fort.latitude+','+fort.longitude;
          info_windows[fort.id] = new google.maps.InfoWindow({
            content: contentString
          });
          google.maps.event.addListener(forts[fort.id], 'click', (function(marker, content, infowindow) {
            return function() {
              infowindow.setContent(content);
              infowindow.open(map, marker);
            };
          })(forts[fort.id], contentString, info_windows[fort.id]));
        }
      }
    }
  }
  if (user_data[users[user_index]].hasOwnProperty('marker') === false) {
    console.log("New Marker: Trainer - " + data.lat + ", " + data.lng);
    randomSex = Math.floor(Math.random() * 1)
    user_data[users[user_index]].marker = new google.maps.Marker({
      map: map,
      position: {lat: parseFloat(data.lat), lng: parseFloat(data.lng)},
      icon: "image/trainer/" + trainerSex[randomSex] + Math.floor(Math.random() * numTrainers[randomSex]) + ".png",
      zIndex: 2,
      label: users[user_index]
    });
  } else {
    user_data[users[user_index]].marker.setPosition({lat: parseFloat(data.lat), lng: parseFloat(data.lng)});
  }
  if (users.length == 1 && userZoom == true) {
    map.setZoom(16);
  }
  if (users.length == 1 && userFollow == true) {
    map.panTo({
      lat: parseFloat(data.lat),
      lng: parseFloat(data.lng)
    });
  }
};

function placeTrainer() {
  for (var i = 0; i < users.length; i++) {
    loadJSON('location-'+users[i]+'.json', trainerFunc, errorFunc, i);
  }
}
function updateTrainer() {
  for (var i = 0; i < users.length; i++) {
    loadJSON('location-'+users[i]+'.json', trainerFunc, errorFunc, i);
  }
}

var catchSuccess = function(data, user_index) {
  if (data !== undefined && Object.keys(data).length > 0) {
    if (user_data[users[user_index]].catchables === undefined) {
      user_data[users[user_index]].catchables = {};
    }
    if (data.latitude !== undefined) {
      if (user_data[users[user_index]].catchables.hasOwnProperty(data.spawnpoint_id) === false) {
        poke_name = pokemonArray[data.pokemon_id-1].Name;
        console.log(poke_name + ' found near user ' + users[user_index]);
        Materialize.toast(poke_name + ' appeared near trainer: ' + users[user_index], 3000, 'rounded')
        user_data[users[user_index]].catchables[data.spawnpoint_id] = new google.maps.Marker({
          map: map,
          position: {lat: parseFloat(data.latitude), lng: parseFloat(data.longitude)},
          icon: "image/pokemon/" + pad_with_zeroes(data.pokemon_id, 3) + imageExt,
          zIndex: 4,
          optimized: false
        });
          if (userZoom == true) {
            map.setZoom(16);
          }
          if (userFollow == true) {
            map.panTo({
              lat: parseFloat(data.latitude),
              lng: parseFloat(data.longitude)
            });
          }
      } else {
        user_data[users[user_index]].catchables[data.spawnpoint_id].setPosition({
          lat: parseFloat(data.latitude),
          lng: parseFloat(data.longitude)
        });
        user_data[users[user_index]].catchables[data.spawnpoint_id].setIcon("image/pokemon/" + pad_with_zeroes(data.pokemon_id, 3) + imageExt);
      }
    }
  } else {
    if (user_data[users[user_index]].catchables !== undefined && Object.keys(user_data[users[user_index]].catchables).length > 0) {
      console.log('No pokemon found near user ' + users[user_index]);
      for (var key in user_data[users[user_index]].catchables) {
        user_data[users[user_index]].catchables[key].setMap(null);
      }
      user_data[users[user_index]].catchables = undefined;
    }
  }
};

function addCatchable() {
  for (var i = 0; i < users.length; i++) {
    loadJSON('catchable-'+users[i]+'.json', catchSuccess, errorFunc, i);
  }
}
function addInventory() {
  for (var i = 0; i < users.length; i++) {
    loadJSON('inventory-'+users[i]+'.json', invSuccess, errorFunc, i);
  }
}

function pad_with_zeroes(number, length) {
  var my_string = '' + number;
  while (my_string.length < length) {
      my_string = '0' + my_string;
  }
  return my_string;
}

function filter(arr, search) {
  var filtered = [];
  for(i=0; i < arr.length; i++) {
    if(arr[i].inventory_item_data[search] != undefined) { filtered.push(arr[i]); };
  }
  return filtered;
}

function loadJSON(path, success, error, successData) {
  var xhr = new XMLHttpRequest();
  xhr.onreadystatechange = function() {
    if (xhr.readyState === XMLHttpRequest.DONE) {
      if (xhr.status === 200) {
        if (success)
          success(JSON.parse(xhr.responseText.replace(/\bNaN\b/g, "null")), successData);
      } else {
        if (error)
        error(xhr);
      }
    }
  };
xhr.open("GET", path, true);
xhr.send();
}

$(document).ready(function(){
  $('.tooltipped').tooltip({delay: 50});
});

function buildMenu() {
  addInventory();
  var data = {};
  if (menu == 1) {
    document.getElementById('subtitle').innerHTML = "Trainer Info";
	data = stats.inventory_item_data.player_stats;
  }
  if (menu == 2) {
    document.getElementById('subtitle').innerHTML = "Items in Bag";
	data = [];
	for(var i in bagItems){
		item = bagItems[i].inventory_item_data.item;
		var it = {};
		console.log(bagItems[i].inventory_item_data)
		it[_ITEMS_[item.item_id]] = item.count || 0;
		data.push(it)

	}
  }
  if (menu == 3) {
    document.getElementById('subtitle').innerHTML = "Pokemon in Bag";
	data = [];
	for(var i in bagPokemon){
		pkmn = bagPokemon[i].inventory_item_data.pokemon_data;
		if(!pkmn.is_egg){
			data.push({
				id: pkmn.id,
				Pokemon: '#'+pkmn.pokemon_id+' '+pokemonArray[pkmn.pokemon_id-1].Name,
				Nickname: pkmn.nickname,
				CP: pkmn.cp,
				IVs: (pkmn.individual_stamina||0)+'/'+(pkmn.individual_attack||0)+'/'+(pkmn.individual_defense||0)
			})
		}
	}
  }
  if (menu == 4) {
    document.getElementById('subtitle').innerHTML = "Pokedex";
	data = pokedex;
  }
  document.getElementById('subcontent').innerHTML = '';
	if($.isArray(data)){
	  for(var i in data){
		  document.getElementById('subcontent').appendChild(prettyPrint(data[i]),{maxDepth:10});
	  }
	}else{
		document.getElementById('subcontent').appendChild(prettyPrint(data),{maxDepth:10});
	}
  
}