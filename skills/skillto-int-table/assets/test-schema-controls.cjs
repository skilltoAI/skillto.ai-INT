const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(__dirname + '/schema-controls.js', 'utf8');
const controls = {'#searchInput':{value:''}, '#tagFilter':{value:''}};
const table = {id:'test', fields:[
  {name:'amount',type:'number'}, {name:'when',type:'date'},
  {name:'enabled',type:'boolean'}, {name:'kind',type:'single_choice'},
  {name:'topics',type:'multiple_choice'}, {name:'picture',type:'image'},
  {name:'videos',type:'short_video_info'}, {name:'name',type:'text'}
], rows:[
  {id:'one',fields:{amount:0,when:'2026-10-01',enabled:false,kind:'A',topics:['x','y'],picture:'',videos:[],name:'Alpha'},tagIds:[]},
  {id:'two',fields:{amount:2.5,when:'2026-10-02',enabled:true,kind:'B',topics:['y'],picture:'https://example.com/a.png',videos:[{id:'v'}],name:'Beta'},tagIds:['tag']},
  {id:'three',fields:{amount:null,when:null},tagIds:[]},
  {id:'four',fields:{amount:'   ',when:''},tagIds:[]}
]};
// Capture the adapter's view through its column-persistence read; no production exports needed.
let map;
class TrackingMap extends Map { constructor(...args) {super(...args);map=this;} }
const context = vm.createContext({Map:TrackingMap,Set,JSON,Number,String,Array,Object,
  state:{table,sort:{field:'amount',direction:1}}, $:s=>controls[s],
  filteredRows:()=>[],renderRows:()=>{}, selectTable:()=>{},
  document:{addEventListener:()=>{}},localStorage:{getItem:()=>null}
});
vm.runInContext(source,context);
context.filteredRows();
const ids = () => Array.from(context.filteredRows(),row=>row.id);
function check(filters, expected) {
  map.get('test').filters=filters;
  assert.deepEqual(ids().sort(),[...expected].sort());
}
check({amount:{min:'0',max:'0'}},['one']);
check({amount:{min:'2.5',max:'2.5'}},['two']);
check({amount:{min:'3',max:'2'}},[]);
check({when:{min:'2026-10-02',max:'2026-10-02'}},['two']);
check({enabled:{value:'no'}},['one']);
check({kind:{value:'B'},topics:{value:'y'},picture:{value:'yes'}},['two']);
check({videos:{value:'no'}},['one','three','four']);
check({videos:{value:'yes'},name:{value:'BETA'}},['two']);
check({},['one','two','three','four']);
controls['#tagFilter'].value='tag';
check({amount:{min:'1'}},['two']);
controls['#tagFilter'].value='';
map.get('test').filters={amount:{min:'100'}};
context.state.table={...table,id:'another'};
assert.equal(context.filteredRows().length,4);
context.state.table=table;
assert.equal(context.filteredRows().length,0);
console.log('Schema controls: 12 boundary, type, combination and table isolation checks passed.');
